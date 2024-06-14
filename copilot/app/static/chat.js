var ws = new WebSocket("ws://localhost:8000/ws");
ws.onmessage = function (event) {
  var messages = document.getElementById("messages");
  var message = document.createElement("li");
  var content = document.createTextNode(event.data);
  message.appendChild(content);
  messages.appendChild(message);
};
function sendMessage(event) {
  var input = document.getElementById("messageText");
  ws.send(input.value);
  input.value = "";
  event.preventDefault();
}
//----
let socket;
var modal;
var can_send = true;
window.onload = () => {
  modal = document.getElementById("loginModal");
  modal.style.display = "block";
  login();
};

async function login() {
  // const username = document.getElementById('username').value;
  // const password = document.getElementById('password').value;
  const url = window.location.pathname.split("/");
  const graphname = url[1];
  const hostname = window.location.hostname;
  const port = window.location.port;

  try {
    // Perform login
    const loginResponse = await fetch(`/${graphname}/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      // body: JSON.stringify({ username, password }),
    });

    const loginData = await loginResponse.json();
    const sessionId = loginData.session_id;

    // Save session ID (you can use sessionStorage, localStorage, or other methods)
    sessionStorage.setItem("sessionId", sessionId);

    // Connect to WebSocket
    var wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";

    socket = new WebSocket(
      wsProtocol +
        `${hostname}:${port}/${graphname}/ws?session_id=${sessionId}`,
    );

    console.log(modal);

    socket.onopen = function (event) {
      console.log("WebSocket is open now.");
      modal.style.display = "none";
    };

    // Handle WebSocket messages
    socket.onmessage = (event) => {
      const chatbox = document.getElementById("chatbox");
      document.getElementById("loader").hidden = true;
      chatbox.innerHTML += `<div class="copilot-container"><p class="copilot-bubble" style="color: white; float: left; text-align: left;">${event.data}</p></div>`;
      chatbox.scrollTop = chatbox.scrollHeight; // Auto-scroll to the bottom
      can_send = true;
    };

    // Handle WebSocket errors
    socket.onerror = (error) => {
      console.error("WebSocket Error:", error);
    };

    // Handle WebSocket closure
    socket.onclose = () => {
      console.log("WebSocket closed");
    };
  } catch (error) {
    console.error("Login failed:", error);
  }
}

function logout() {
  const url2 = window.location.pathname.split("/");
  const graphname = url2[1];
  // Close WebSocket connection
  if (socket) {
    socket.close();
  }

  // Perform logout (adjust the URL and method based on your API)
  const sessionId = sessionStorage.getItem("sessionId");
  const url = `/${graphname}/logout?session_id=${sessionId}`;

  fetch(url, { method: "POST" })
    .then((response) => response.json())
    .then((data) => {
      console.log("Logout successful:", data);
    })
    .catch((error) => {
      console.error("Logout failed:", error);
    });

  // Clear session ID from storage
  sessionStorage.removeItem("sessionId");

  modal = document.getElementById("loginModal");
  modal.style.display = "block";
}

function handleKeyup(event) {
  if (event.key === "Enter") {
    // If Enter key is pressed, send the message
    sendMessage();
  }
}

function sendMessage() {
  const messageInput = document.getElementById("messageInput");
  const message = messageInput.value;

  if (message.trim() !== "" && can_send == true) {
    // Display your message in the chatbox
    const chatbox = document.getElementById("chatbox");
    chatbox.innerHTML += `<div class="message-container"><p id="message-bubble" style="color: white; float: right; text-align: right;">${message}</p></div>`;
    document.getElementById("loader").hidden = false;
    chatbox.scrollTop = chatbox.scrollHeight; // Auto-scroll to the bottom

    // Send message through WebSocket
    socket.send(message);
    can_send = false;
    // Clear input field
    messageInput.value = "";
  }
}
