class FeedbackModel {
    constructor() {
        this.sessionId = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.transcript = '';
        this.isRecording = false;
        this.feedbackHistory = [];
    }

    async startSession() {
        try {
            const response = await fetch('/api/feedback/start', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                }
            });
            if (!response.ok) {
                showStatus('Failed to start session. Please log in again.', true);
                return false;
            }
            const data = await response.json();
            this.sessionId = data.session_id;
            return true;
        } catch (error) {
            showStatus('Error starting feedback session.', true);
            console.error('Error starting feedback session:', error);
            return false;
        }
    }

    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            
            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };
            
            this.mediaRecorder.onstop = async () => {
                await this.processAudio();
            };
            
            this.mediaRecorder.start();
            this.isRecording = true;
            return true;
        } catch (error) {
            console.error('Error starting recording:', error);
            return false;
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
            this.isRecording = false;
            return true;
        }
        return false;
    }

    async processAudio() {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
        const formData = new FormData();
        formData.append('audio', audioBlob);
        formData.append('session_id', this.sessionId);
        
        try {
            const response = await fetch('/api/feedback/transcript', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: formData
            });
            const data = await response.json();
            if (data.transcript) {
                this.transcript += data.transcript + '\n';
                return data.transcript;
            }
        } catch (error) {
            console.error('Error processing audio:', error);
            return null;
        }
    }

    async submitFeedback(content, rating = null, feedbackType = 'general') {
        try {
            const response = await fetch('/api/feedback/submit', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content,
                    rating,
                    feedback_type: feedbackType
                })
            });
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error submitting feedback:', error);
            return null;
        }
    }

    reset() {
        this.sessionId = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.transcript = '';
        this.isRecording = false;
    }
}

// Instantiate the feedback model for use throughout the file
const feedbackModel = new FeedbackModel();

// Export the model
window.FeedbackModel = FeedbackModel;

// Feedback conversation logic (identical to interview scripts, with feedback prompt)
let peerConnection, dataChannel, isSessionReady = false;
const transcriptLog = [];
let sessionTimeout;
let userBuffer = "";
let aiBuffer = "";
let hasEnded = false;
let isInstructionsApplied = false;
let userName = "there"; // fallback

const audioElement = document.getElementById("aiAudio");
const startButton = document.getElementById("startFeedback");
const stopButton = document.getElementById("stopFeedback");
const statusEl = document.getElementById("feedbackStatus");
const transcriptEl = document.getElementById("feedbackTranscript");

function showStatus(msg, isError = false) {
  if (statusEl) {
    statusEl.textContent = msg;
    statusEl.style.color = isError ? '#dc3545' : '#06B6D4';
  }
}

function isFarewell(text) {
  const cleaned = text.toLowerCase().trim();
  return ["goodbye", "see you", "talk to you later", "i have to go"].some(phrase =>
    cleaned === phrase ||
    cleaned.startsWith(phrase + ".") ||
    cleaned.startsWith(phrase + "!") ||
    cleaned.startsWith(phrase + ",") ||
    cleaned.includes(" " + phrase + " ")
  );
}

async function endConversation(reason) {
  if (hasEnded) return;
  hasEnded = true;

  if (sessionTimeout) clearTimeout(sessionTimeout);
  console.log("Conversation ended:", reason);
  statusEl.textContent = "Feedback session complete";

  // Save feedback transcript
  fetch('/api/feedback/submit', {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content: transcriptLog.map(e => `${e.speaker}: ${e.text}`).join("\n"),
      feedback_type: "voice_feedback"
    })
  })
  .then(res => res.json())
  .then(data => {
    console.log("✅ Feedback saved:", data);
  })
  .catch(err => console.error("❌ Failed to save feedback", err));

  // Clean up WebRTC
  if (dataChannel) dataChannel.close();
  if (peerConnection) peerConnection.close();
  if (window.localStream) {
    window.localStream.getTracks().forEach(track => track.stop());
    window.localStream = null;
  }
  stopButton.disabled = true;
  startButton.disabled = false;
}

async function fetchUserName() {
  try {
    const res = await fetch('/api/user');
    const data = await res.json();
    if (data.user && data.user.first_name && data.user.last_name) {
      userName = `${data.user.first_name} ${data.user.last_name}`.trim();
      console.log("✅ Feedback agent using user name:", userName);
    } else {
      console.warn("⚠️ No user name found, using fallback");
      userName = "there";
    }
  } catch (e) {
    console.error("❌ Error fetching user name:", e);
    userName = "there";
  }
}

// Call this before starting the session
fetchUserName();

// Use a placeholder in the instructions
const feedbackInstructionsTemplate = `
INSTRUCTIONS:
You are an AI feedback collector for Story Boom AI, a tool that helps create case studies. Greet the user by name: {USER_NAME}.

STYLE:
- Be warm and friendly
- Ask ONE question and then let the user talk freely
- Don't ask follow-up questions
- Just listen and let them share

CONVERSATION FLOW:

[1. GREETING & INTRODUCTION]
- Greet the user warmly by name ({USER_NAME})
- Introduce yourself briefly as the Story Boom AI feedback assistant

[2. SINGLE QUESTION]
- Ask: "How has your experience been with Story Boom AI so far?"
- Then be quiet and let them talk as long as they want

[3. CLOSING]
- When they seem done talking, ask: "Is there anything else you'd like to add?"
- If they say no, thank them and say goodbye
- If they have more to share, let them continue

IMPORTANT:
- Ask only ONE main question
- Don't ask follow-up questions
- Let the user talk freely without interruption
- Just listen and acknowledge occasionally
- End when they're done sharing
`;

function getPersonalizedInstructions() {
  return feedbackInstructionsTemplate.replaceAll('{USER_NAME}', userName);
}

async function initConnection() {
  try {
    const res = await fetch("/session");
    const data = await res.json();
    const EPHEMERAL_KEY = data.client_secret.value;

    peerConnection = new RTCPeerConnection();
    window.localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audioTrack = localStream.getAudioTracks()[0];
    peerConnection.addTrack(audioTrack, localStream);

    peerConnection.ontrack = (event) => {
      const [remoteStream] = event.streams;
      const remoteOnly = new MediaStream();
      remoteStream.getAudioTracks().forEach(track => {
        if (track.kind === "audio" && track.label !== "Microphone") {
          remoteOnly.addTrack(track);
        }
      });
      audioElement.srcObject = remoteOnly;
    };

    dataChannel = peerConnection.createDataChannel("openai-events");

    dataChannel.onopen = () => {
      dataChannel.send(JSON.stringify({
        type: "session.update",
        session: {
          instructions: getPersonalizedInstructions(),
          voice: "coral",
          modalities: ["audio", "text"],
          input_audio_transcription: { model: "whisper-1" },
          turn_detection: { type: "server_vad" }
        }
      }));
    };

    dataChannel.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      handleMessage(event);

      if (msg.type === "session.updated" && !isInstructionsApplied) {
        isInstructionsApplied = true;
        statusEl.textContent = "✅ Ready to collect your feedback";
        dataChannel.send(JSON.stringify({
          type: "response.create",
          response: {
            modalities: ["audio", "text"],
            input: [
              {
                type: "message",
                role: "user",
                content: [
                  { type: "input_text", text: "Hi! I'd like to share my feedback about Story Boom AI." }
                ]
              }
            ]
          }
        }));
        sessionTimeout = setTimeout(() => {
          endConversation("⏱️ 3-minute limit reached.");
        }, 3 * 60 * 1000);
      }
    };

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);

    const response = await fetch("https://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${EPHEMERAL_KEY}`,
        "Content-Type": "application/sdp"
      },
      body: offer.sdp
    });

    const answer = await response.text();
    await peerConnection.setRemoteDescription({ type: "answer", sdp: answer });

    isSessionReady = true;
    statusEl.textContent = "🔄 Connecting to AI...";
    stopButton.classList.remove("hidden");
    stopButton.disabled = false;
    startButton.disabled = true;
  } catch (err) {
    statusEl.textContent = "❌ Failed to start session.";
    console.error(err);
  }
}

function handleMessage(event) {
  const msg = JSON.parse(event.data);
  switch (msg.type) {
    case "response.audio_transcript.done":
      if (msg.transcript) {
        transcriptLog.push({ speaker: "ai", text: msg.transcript });
        aiBuffer = "";
      }
      break;
    case "conversation.item.input_audio_transcription.completed":
      if (msg.transcript && !hasEnded) {
        transcriptLog.push({ speaker: "user", text: msg.transcript });
        const cleanedText = msg.transcript.toLowerCase().trim();
        userBuffer = "";
        if (isFarewell(cleanedText)) {
          console.log("👋 Detected farewell from user.");
          endConversation("👋 User said farewell.");
        }
      }
      break;
  }
}

if (startButton && stopButton) {
  startButton.addEventListener("click", async () => {
    console.log('[DEBUG] Start Conversation button clicked');
    statusEl.textContent = 'Starting feedback session...';
    await initConnection();
  });
  stopButton.addEventListener("click", () => {
    console.log('[DEBUG] Stop Conversation button clicked');
    endConversation("🛑 Manual end by user.");
  });
} 