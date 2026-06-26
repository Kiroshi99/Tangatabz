const gate = document.getElementById("gate");
const app = document.getElementById("app");

const music = document.getElementById("music");
const musicButton = document.getElementById("musicButton");
const musicStatus = document.getElementById("musicStatus");
const musicAudio = document.getElementById("musicAudio");

const volumeSlider = document.getElementById("volumeSlider");
const volumeValue = document.getElementById("volumeValue");

/* Default music volume: 5% */
let currentVolume = 5;

musicAudio.volume = currentVolume / 100;
volumeSlider.value = currentVolume;
volumeValue.textContent = `${currentVolume}%`;

function updateMusicUI(isPlaying, customStatus = "") {
  music.classList.toggle("playing", isPlaying);

  musicButton.setAttribute(
    "aria-label",
    isPlaying ? "Pause music" : "Play music"
  );

  if (customStatus) {
    musicStatus.textContent = customStatus;
    return;
  }

  if (isPlaying) {
    musicStatus.textContent = `LOVE MODE · ${currentVolume}%`;
  } else {
    musicStatus.textContent = `PAUSED · ${currentVolume}%`;
  }
}

function setVolume(value) {
  currentVolume = Number(value);

  musicAudio.volume = currentVolume / 100;
  volumeSlider.value = currentVolume;
  volumeValue.textContent = `${currentVolume}%`;

  if (!musicAudio.paused) {
    musicStatus.textContent = `LOVE MODE · ${currentVolume}%`;
  } else {
    musicStatus.textContent = `PAUSED · ${currentVolume}%`;
  }
}

async function startMusic() {
  try {
    await musicAudio.play();
    updateMusicUI(true);
  } catch (error) {
    console.warn("Music could not start:", error);
    updateMusicUI(false, "TAP PLAY · 5%");
  }
}

function unlock() {
  if (gate.classList.contains("hide")) {
    return;
  }

  app.setAttribute("aria-hidden", "false");
  document.body.classList.remove("locked");
  gate.classList.add("hide");

  /* Starts immediately after the user clicks the gate */
  startMusic();
}

gate.addEventListener("click", unlock);

gate.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    unlock();
  }
});

musicButton.addEventListener("click", async () => {
  if (musicAudio.paused) {
    await startMusic();
  } else {
    musicAudio.pause();
  }
});

volumeSlider.addEventListener("input", (event) => {
  setVolume(event.target.value);
});

musicAudio.addEventListener("play", () => {
  updateMusicUI(true);
});

musicAudio.addEventListener("pause", () => {
  updateMusicUI(false);
});

musicAudio.addEventListener("error", () => {
  console.error("Could not find the music file.");
  updateMusicUI(false, "AUDIO FILE MISSING");
});

document.getElementById("year").textContent = new Date().getFullYear();

const reveals = document.querySelectorAll(".reveal");

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("show");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12 }
);

reveals.forEach((element) => observer.observe(element));

window.addEventListener(
  "pointermove",
  (event) => {
    document.documentElement.style.setProperty("--mx", `${event.clientX}px`);
    document.documentElement.style.setProperty("--my", `${event.clientY}px`);
  },
  { passive: true }
);

const canvas = document.getElementById("heartCanvas");
const ctx = canvas.getContext("2d");

let width = 0;
let height = 0;
let dpr = 1;
let hearts = [];
let sparkles = [];

function random(min, max) {
  return Math.random() * (max - min) + min;
}

function setupCanvas() {
  width = window.innerWidth;
  height = window.innerHeight;
  dpr = Math.min(window.devicePixelRatio || 1, 2);

  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const heartCount = Math.min(
    48,
    Math.max(22, Math.floor((width * height) / 38000))
  );

  hearts = Array.from({ length: heartCount }, () => ({
    x: random(0, width),
    y: random(0, height),
    size: random(3, 11),
    speed: random(0.08, 0.34),
    alpha: random(0.08, 0.34),
    angle: random(-0.6, 0.6),
    spin: random(-0.0018, 0.0018),
    phase: random(0, Math.PI * 2)
  }));

  const sparkleCount = Math.min(
    60,
    Math.max(25, Math.floor((width * height) / 27000))
  );

  sparkles = Array.from({ length: sparkleCount }, () => ({
    x: random(0, width),
    y: random(0, height),
    size: random(0.5, 1.8),
    alpha: random(0.08, 0.35),
    phase: random(0, Math.PI * 2)
  }));
}

function drawHeart(x, y, size, alpha, angle) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle);

  ctx.beginPath();
  ctx.moveTo(0, size * 0.35);

  ctx.bezierCurveTo(
    -size * 1.3,
    -size * 0.45,
    -size * 0.95,
    -size * 1.25,
    0,
    -size * 0.45
  );

  ctx.bezierCurveTo(
    size * 0.95,
    -size * 1.25,
    size * 1.3,
    -size * 0.45,
    0,
    size * 0.35
  );

  ctx.closePath();
  ctx.fillStyle = `rgba(255, 132, 172, ${alpha})`;
  ctx.fill();

  ctx.restore();
}

function draw(time = 0) {
  ctx.clearRect(0, 0, width, height);

  sparkles.forEach((sparkle) => {
    const flicker = 0.45 + 0.55 * Math.sin(time * 0.0013 + sparkle.phase);

    ctx.beginPath();
    ctx.arc(
      sparkle.x,
      sparkle.y,
      sparkle.size * flicker,
      0,
      Math.PI * 2
    );

    ctx.fillStyle = `rgba(255, 218, 228, ${sparkle.alpha * flicker})`;
    ctx.fill();
  });

  hearts.forEach((item) => {
    item.y -= item.speed;
    item.x += Math.sin(time * 0.0006 + item.phase) * 0.22;
    item.angle += item.spin;

    if (item.y < -30) {
      item.y = height + 30;
      item.x = random(0, width);
    }

    drawHeart(item.x, item.y, item.size, item.alpha, item.angle);
  });

  requestAnimationFrame(draw);
}

window.addEventListener("resize", setupCanvas, { passive: true });

setupCanvas();
draw();