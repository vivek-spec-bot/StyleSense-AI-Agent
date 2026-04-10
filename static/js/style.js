const state = {
  wardrobe: [],
  history: [],
  auth: null,
  location: null,
  tryOnSnapshot: null,
  lastRecommendation: null,
  selectedOutfit: null,
};

const page = document.body.dataset.page;
let activeFeatureId = "overview";

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Something went wrong.");
  }
  return data;
}

function jsonRequest(path, method, payload) {
  return api(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function formRequest(path, method, formData) {
  const response = await fetch(path, {
    method,
    body: formData,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Something went wrong.");
  }
  return data;
}

function setLoaded(selector) {
  const element = document.querySelector(selector);
  if (element) {
    element.classList.add("loaded");
  }
}

function activateFeature(sectionId) {
  if (page !== "home") return;
  const targetId = sectionId || "overview";
  activeFeatureId = targetId;
  const targetPanel = document.querySelector(`[data-feature-panel="${targetId}"]`);
  const targetGroup = targetPanel?.closest(".feature-group") || document.getElementById(targetId)?.closest(".feature-group") || (document.getElementById(targetId)?.classList.contains("feature-group") ? document.getElementById(targetId) : null);
  document.querySelectorAll("[data-feature-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.featurePanel === targetId);
  });
  document.querySelectorAll(".feature-group").forEach((group) => {
    group.classList.toggle("active", targetId === "overview" ? false : group === targetGroup || group.id === targetId);
  });
  if (targetGroup && targetGroup.classList.contains("feature-group")) {
    targetGroup.classList.add("active");
  }
  if (targetId === "overview") {
    document.querySelectorAll(".feature-group").forEach((group) => group.classList.remove("active"));
  }
  document.querySelectorAll("[data-section-target]").forEach((link) => {
    const isActive = link.dataset.sectionTarget === targetId;
    link.classList.toggle("active", isActive);
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function metricCard(item) {
  return `<article class="metric-card"><span>${item.label}</span><strong>${item.value}</strong></article>`;
}

function wardrobeCard(item) {
  const tags = [item.category, item.color, item.fabric, item.occasion]
    .filter(Boolean)
    .map((value) => `<span class="tag">${value}</span>`)
    .join("");
  const image = item.image_url ? `<img src="${item.image_url}" alt="${item.name}">` : "";
  return `
    <article class="info-card">
      ${image}
      <h3>${item.name}</h3>
      <p>${item.image_hint || "Tagged wardrobe piece"}</p>
      <div class="tag-row">${tags}</div>
      <p class="status-note">Worn ${item.times_worn || 0} times</p>
      <button class="ghost-button favorite-button" data-favorite-id="${item.id}">${item.favorite ? "Favorited" : "Add to Favorites"}</button>
      <button class="ghost-button danger-button favorite-button" data-delete-id="${item.id}">Delete Item</button>
    </article>
  `;
}

function historyCard(item) {
  const items = (item.items || []).map((entry) => `<span class="tag">${entry}</span>`).join("");
  return `
    <article class="timeline-item">
      <h3>${item.name}</h3>
      <p>${item.date} | ${item.occasion} | Score ${item.score}</p>
      <div class="tag-row">${items}</div>
      ${item.style_request ? `<p class="status-note">Your brief: ${item.style_request}</p>` : ""}
    </article>
  `;
}

function outfitGalleryCard(item) {
  const items = (item.items || []).map((entry) => `<span class="tag">${entry}</span>`).join("");
  return `
    <article class="info-card outfit-card">
      <h3>${item.name}</h3>
      <p>${item.date} | ${item.occasion} | Score ${item.score}</p>
      <div class="tag-row">${items}</div>
      ${item.style_request ? `<p class="status-note">Brief: ${item.style_request}</p>` : ""}
      <div class="inline-form outfit-actions">
        <button class="ghost-button" data-tryon-outfit-id="${item.id}">Try On</button>
        <button class="primary-button" data-add-outfit-id="${item.id}">Add To Wardrobe</button>
      </div>
    </article>
  `;
}

function renderWardrobe() {
  const grid = document.getElementById("wardrobeGrid");
  if (!grid) return;
  grid.innerHTML = state.wardrobe.length ? state.wardrobe.map(wardrobeCard).join("") : `<article class="info-card"><h3>No wardrobe items yet</h3><p>Add a piece above to start building your closet.</p></article>`;
  setLoaded("#wardrobeGrid");
}

function renderOutfitGallery() {
  const grid = document.getElementById("outfitGallery");
  if (!grid) return;
  grid.innerHTML = state.history.length
    ? state.history.map(outfitGalleryCard).join("")
    : `<article class="info-card"><h3>No generated outfits yet</h3><p>Run the AI stylist to create full looks you can choose from here.</p></article>`;
  setLoaded("#outfitGallery");
}

function renderHistory() {
  const list = document.getElementById("historyList");
  if (!list) return;
  list.innerHTML = state.history.length ? state.history.map(historyCard).join("") : `<article class="timeline-item"><h3>No saved outfits yet</h3><p>Generate a styling brief or weather outfit to populate the timeline.</p></article>`;
  setLoaded("#historyList");
}

function renderFeatureGroups(groups) {
  const container = document.getElementById("featureGroups");
  if (!container) return;
  container.innerHTML = groups
    .map(
      (group) => `
      <article class="info-card">
        <h3>${group.title}</h3>
        <ul>${group.items.map((item) => `<li>${item}</li>`).join("")}</ul>
      </article>
    `
    )
    .join("");
  setLoaded("#featureGroups");
}

function renderDiscovery(results) {
  const container = document.getElementById("discoverResult");
  if (!container) return;
  container.innerHTML = results
    .map(
      (entry) => `
      <article class="info-card">
        <h3>${entry.title}</h3>
        <p>${entry.creator} | ${entry.style}</p>
        <div class="tag-row">
          <span class="tag">${entry.trend}</span>
          <span class="tag">${entry.likes} likes</span>
          <span class="tag">${entry.saves} saves</span>
        </div>
      </article>
    `
    )
    .join("");
  setLoaded("#discoverResult");
}

function renderLookbook(data) {
  const panel = document.getElementById("lookbookResult");
  if (!panel) return;
  panel.innerHTML = `
    <strong>${data.theme}</strong>
    <ul>${data.looks.map((look) => `<li>${look.title}: ${look.description}</li>`).join("")}</ul>
    <p class="status-note">${data.image_generation_note}</p>
  `;
  panel.classList.add("loaded");
}

function renderRecommendation(data) {
  state.lastRecommendation = data;
  const panel = document.getElementById("recommendResult");
  if (!panel) return;
  const accessories = (data.accessories || data.recommendation.accessories || []).map((entry) => `<span class="tag">${entry}</span>`).join("");
  const generatedScore = Number(data.compatibility_score || 0);
  const generatedWidth = Math.max(0, Math.min(100, generatedScore));
  panel.innerHTML = `
    <div class="compatibility-compare">
      <div class="compatibility-column">
        <span class="compatibility-label">Generated compatibility</span>
        <strong>${generatedScore}%</strong>
        <div class="compatibility-track"><div class="compatibility-fill" style="width:${generatedWidth}%"></div></div>
      </div>
    </div>
    <p>${data.summary}</p>
    ${data.reference_image_url ? `<div class="reference-image-card"><img src="${data.reference_image_url}" alt="${data.reference_image_name || "Style reference"}"><span>Reference image used by the AI stylist</span></div>` : ""}
    <div class="tag-row">
      <span class="tag">${data.recommendation.top}</span>
      <span class="tag">${data.recommendation.bottom}</span>
      <span class="tag">${data.recommendation.shoes}</span>
      <span class="tag">${data.recommendation.layer}</span>
      ${accessories}
    </div>
    <ul>
      <li>${data.outfit_reasoning}</li>
      <li>${data.daily_suggestion}</li>
      <li>${data.wardrobe_gap}</li>
    </ul>
    ${data.style_request ? `<p class="status-note">Saved from your brief: ${data.style_request}</p>` : ""}
    ${data.image_inspired_note ? `<p class="status-note">${data.image_inspired_note}</p>` : ""}
    <p class="status-note">Gender: ${data.gender} | Fabric: ${data.preferred_fabric} | Style: ${data.dress_style}</p>
    <p class="status-note">Budget: ${data.budget || "1000"} | ${data.budget_phrase || "budget-friendly in India"}</p>
    <p class="status-note">Capsule builder: ${data.capsule_builder.join(", ")}</p>
    <div class="inline-form recommendation-actions">
      <button id="applyTryOnButton" class="primary-button" type="button">Try On This Outfit</button>
      <button id="saveRecommendationButton" class="ghost-button" type="button">Add Outfit To Wardrobe</button>
    </div>
  `;
  panel.classList.add("loaded");
  renderWebOutfitSuggestions(data.web_outfit_suggestions || []);
}

function renderWebOutfitSuggestions(groups) {
  const container = document.getElementById("webOutfitSuggestions");
  if (!container) return;
  if (!groups.length || !groups.some((group) => group.products && group.products.length)) {
    container.innerHTML = `
      <article class="info-card">
        <h3>Web outfit sourcing</h3>
        <p>Add <code>SERPAPI_API_KEY</code> to your <code>.env</code> to get live AI-ranked shopping suggestions from the web. Results are filtered toward India-friendly shopping when enabled.</p>
      </article>
    `;
    container.classList.add("loaded");
    return;
  }
  container.innerHTML = groups
    .map((group) => {
      const cards = group.products
        .map(
          (product) => `
          <article class="info-card">
            ${product.thumbnail ? `<img src="${product.thumbnail}" alt="${product.title}">` : ""}
            <h3>${product.title}</h3>
            <p>${group.category}: ${group.piece}</p>
            <div class="tag-row">
              <span class="tag">${product.source}</span>
              <span class="tag">${product.price}</span>
              ${product.rating ? `<span class="tag">${product.rating} stars</span>` : ""}
            </div>
            <p class="status-note">India-friendly search</p>
            ${product.link ? `<a class="product-link" href="${product.link}" target="_blank" rel="noopener noreferrer">Open Product</a>` : ""}
          </article>
        `
        )
        .join("");
      return `<section class="section-grid single-column"><article class="panel"><div class="section-heading"><span class="eyebrow">${group.category}</span><h2>${group.piece}</h2></div><div class="card-grid">${cards}</div></article></section>`;
    })
    .join("");
  container.classList.add("loaded");
}

function renderTryOn(data) {
  const panel = document.getElementById("tryOnResult");
  if (!panel) return;
  panel.innerHTML = `
    <strong>${data.avatar}</strong>
    <p>${data.simulation.overlay_quality} | Body map confidence ${data.simulation.body_map_confidence}</p>
    <ul>${data.fit_notes.map((note) => `<li>${note}</li>`).join("")}</ul>
    <p class="status-note">Preview layers: ${data.preview_layers.map((layer) => `${layer.name} on ${layer.position}`).join("; ")}</p>
    <p class="status-note">Fit balance: ${data.calibration.fit_balance}% | ${data.calibration.distance} camera distance | ${data.calibration.posture} posture</p>
  `;
  panel.classList.add("loaded");
  renderTryOnOverlay(data.overlay_layout);
}

async function tryOnRecommendation() {
  const recommendation = state.lastRecommendation;
  if (!recommendation?.recommendation) {
    showStatus("cameraStatus", "Generate an outfit first, then try it on.", true);
    return;
  }
  const tryOnForm = document.getElementById("tryOnForm");
  if (tryOnForm instanceof HTMLFormElement) {
    const topField = tryOnForm.elements.namedItem("top");
    const bottomField = tryOnForm.elements.namedItem("bottom");
    if (topField instanceof HTMLInputElement) topField.value = recommendation.recommendation.top || topField.value;
    if (bottomField instanceof HTMLInputElement) bottomField.value = recommendation.recommendation.bottom || bottomField.value;
  }
  const video = document.getElementById("cameraPreview");
  const framePayload =
    state.tryOnSnapshot ||
    (video && video.videoWidth && video.videoHeight
      ? { frame_width: video.videoWidth, frame_height: video.videoHeight }
      : { frame_width: 720, frame_height: 960 });
  const payload = {
    top: recommendation.recommendation.top,
    bottom: recommendation.recommendation.bottom,
    avatar: "StyleSense AI Outfit",
    body_type: recommendation.style_request ? "Personalized" : "Athletic",
    fit: "True to size",
    height_cm: 172,
    shoulder_cm: 46,
    waist_cm: 80,
    inseam_cm: 78,
    camera_distance: "Medium",
    posture: "Neutral",
    ...framePayload,
  };
  renderTryOn(await jsonRequest("/api/try-on", "POST", payload));
  showStatus("cameraStatus", "AI stylist outfit sent to virtual try-on.");
}

function parseOutfitItems(outfit) {
  const items = outfit.items || [];
  return {
    top: items[0] || outfit.top || "Relaxed Tee",
    bottom: items[1] || outfit.bottom || "Wide Leg Trouser",
    shoes: items[2] || outfit.shoes || "Minimal Sneaker",
    layer: items[3] || outfit.layer || "Light Layer",
    accessories: items.slice(4),
  };
}

function storeTryOnDraft(outfit) {
  const parsed = parseOutfitItems(outfit);
  sessionStorage.setItem(
    "stylesense.tryOnDraft",
    JSON.stringify({
      top: parsed.top,
      bottom: parsed.bottom,
      shoes: parsed.shoes,
      layer: parsed.layer,
      accessories: parsed.accessories,
      avatar: "StyleSense AI Outfit",
      body_type: "Personalized",
      fit: "True to size",
      height_cm: 172,
      shoulder_cm: 46,
      waist_cm: 80,
      inseam_cm: 78,
      camera_distance: "Medium",
      posture: "Neutral",
    })
  );
}

async function saveRecommendationToWardrobe() {
  const recommendation = state.lastRecommendation;
  if (!recommendation) {
    showStatus("uploadStatus", "Generate an outfit first, then add it to the wardrobe.", true);
    return;
  }
  const payload = {
    outfit: {
      name: recommendation.saved_outfit?.name || "AI Styled Look",
      occasion: recommendation.occasion,
      weather: recommendation.weather,
      top: recommendation.recommendation?.top,
      bottom: recommendation.recommendation?.bottom,
      shoes: recommendation.recommendation?.shoes,
      layer: recommendation.recommendation?.layer,
      accessories: recommendation.accessories || recommendation.recommendation?.accessories || [],
      preferred_fabric: recommendation.preferred_fabric,
      fabric: recommendation.preferred_fabric,
      color: "Neutral",
      pattern: "Solid",
    },
  };
  const response = await jsonRequest("/api/recommend/save-to-wardrobe", "POST", payload);
  showStatus("uploadStatus", `Added ${response.added_items.length} outfit pieces to the wardrobe.`);
  await refreshState();
}

function updateImagePreview(previewId, file, fallbackMessage) {
  const preview = document.getElementById(previewId);
  if (!preview) return;
  if (!file) {
    preview.innerHTML = `<span class="status-note">${fallbackMessage}</span>`;
    return;
  }
  const objectUrl = URL.createObjectURL(file);
  preview.innerHTML = `
    <div class="reference-image-card">
      <img src="${objectUrl}" alt="${file.name}">
      <span>${file.name}</span>
    </div>
  `;
}

function updateStylistImagePreview(file) {
  updateImagePreview("stylistReferencePreview", file, "Upload a style image and the AI stylist will use it to shape a similar outfit result.");
}

function renderChat(data) {
  const panel = document.getElementById("chatResult");
  if (!panel) return;
  panel.innerHTML = `
    <strong>Stylist Reply</strong>
    <p>${data.reply}</p>
    <div class="tag-row">${data.memory.map((item) => `<span class="tag">${item}</span>`).join("")}</div>
  `;
  panel.classList.add("loaded");
}

function renderWeatherOutfit(data) {
  const panel = document.getElementById("weatherOutfitResult");
  if (!panel) return;
  const weather = data.weather_report;
  panel.innerHTML = `
    <strong>${weather.location_label}</strong>
    <p>${weather.description} | ${weather.temperature}C | Feels like ${weather.feels_like}C</p>
    <div class="tag-row">
      <span class="tag">${data.recommendation.top}</span>
      <span class="tag">${data.recommendation.bottom}</span>
      <span class="tag">${data.recommendation.shoes}</span>
      <span class="tag">${weather.weather_label}</span>
    </div>
    <ul>
      <li>${data.summary}</li>
      <li>${data.outfit_reasoning}</li>
      <li>${data.daily_suggestion}</li>
    </ul>
  `;
  panel.classList.add("loaded");
}

function renderAnalytics(data) {
  const stats = document.getElementById("analyticsStats");
  const charts = document.getElementById("analyticsCharts");
  const insights = document.getElementById("analyticsInsights");
  if (!stats || !charts || !insights) return;

  stats.innerHTML = data.statistics.map(metricCard).join("");
  charts.innerHTML = `
    <article class="panel">
      <div class="section-heading"><h2>Category Usage</h2></div>
      <div class="bar-list">
        ${data.category_breakdown
          .map(
            (item) => `
          <div class="bar-row">
            <span>${item.name} (${item.count})</span>
            <div class="bar-track"><div class="bar-fill" style="width:${item.count * 20}%"></div></div>
          </div>
        `
          )
          .join("")}
      </div>
    </article>
    <article class="panel">
      <div class="section-heading"><h2>Color Usage</h2></div>
      <div class="bar-list">
        ${data.color_breakdown
          .map(
            (item) => `
          <div class="bar-row">
            <span>${item.name} (${item.count})</span>
            <div class="bar-track"><div class="bar-fill" style="width:${item.count * 20}%"></div></div>
          </div>
        `
          )
          .join("")}
      </div>
    </article>
  `;
  insights.innerHTML = data.insights.map((item) => `<article class="insight-item"><p>${item}</p></article>`).join("");
  setLoaded("#analyticsStats");
  setLoaded("#analyticsInsights");
}

function renderAuth(authState) {
  state.auth = authState;
  const badge = document.getElementById("authBadge");
  const summary = document.getElementById("authSummary");
  const logoutButton = document.getElementById("logoutButton");
  if (badge) {
    badge.textContent = authState.authenticated ? `Signed In: ${authState.user.name}` : "Demo Mode";
  }
  if (summary) {
    summary.innerHTML = authState.authenticated
      ? `<strong>${authState.user.name}</strong><p>${authState.user.email} | ${authState.user.style_personality}</p>`
      : "<strong>Demo profile active</strong><p>Create an account or login to keep your own wardrobe and styling history.</p>";
  }
  if (logoutButton) {
    logoutButton.classList.toggle("hidden", !authState.authenticated);
  }
}

function showStatus(id, message, isError = false) {
  const element = document.getElementById(id);
  if (!element) return;
  element.textContent = message;
  element.style.color = isError ? "#ff9b8d" : "";
}

function renderTryOnOverlay(layout) {
  const overlay = document.getElementById("tryOnOverlay");
  const topBox = document.getElementById("overlayTop");
  const bottomBox = document.getElementById("overlayBottom");
  const shoulderLine = document.querySelector(".guide-shoulder");
  const waistLine = document.querySelector(".guide-waist");
  if (!overlay || !topBox || !bottomBox || !shoulderLine || !waistLine || !layout) return;

  overlay.classList.remove("hidden");
  shoulderLine.style.top = `${layout.guides.shoulder_line}%`;
  waistLine.style.top = `${layout.guides.waist_line}%`;

  const applyBox = (element, box) => {
    element.style.left = `${box.x}%`;
    element.style.top = `${box.y}%`;
    element.style.width = `${box.width}%`;
    element.style.height = `${box.height}%`;
    element.dataset.label = box.label;
  };

  applyBox(topBox, layout.top);
  applyBox(bottomBox, layout.bottom);
}

async function requestWeatherOutfitWithLocation(notify = false) {
  if (!navigator.geolocation) {
    showStatus("weatherStatus", "Geolocation is not supported in this browser.", true);
    return;
  }
  showStatus("weatherStatus", "Reading your location so the UI can personalize your outfit context...");
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      try {
        state.location = {
          lat: position.coords.latitude,
          lon: position.coords.longitude,
          location_label: `Near ${position.coords.latitude.toFixed(2)}, ${position.coords.longitude.toFixed(2)}`,
        };
        const summary = document.getElementById("locationSummary");
        if (summary) {
          summary.textContent = `Location shared: ${state.location.location_label}. Weather selections below will be tailored to your local context.`;
        }
        const weatherForm = document.getElementById("weatherContextForm");
        if (weatherForm instanceof HTMLFormElement) {
          const payload = formToJson(weatherForm);
          const result = await jsonRequest("/api/weather-outfit", "POST", { ...state.location, ...payload });
          renderWeatherOutfit(result);
          showStatus("weatherStatus", "Local outfit report generated from your selected conditions.");
          if (notify && "Notification" in window && Notification.permission === "granted") {
            new Notification("StyleSense Weather Outfit", { body: result.notification });
          }
          await refreshState();
        }
      } catch (error) {
        showStatus("weatherStatus", error.message, true);
      }
    },
    (error) => {
      showStatus("weatherStatus", `Location access failed: ${error.message}`, true);
    },
    { enableHighAccuracy: true, timeout: 12000, maximumAge: 300000 }
  );
}

async function requestNotificationPermission() {
  if (!("Notification" in window)) {
    showStatus("weatherStatus", "Notifications are not supported in this browser.", true);
    return;
  }
  const permission = await Notification.requestPermission();
  if (permission === "granted") {
    showStatus("weatherStatus", "Notifications enabled. Weather outfit alerts will appear on open.");
    await requestWeatherOutfitWithLocation(true);
  } else {
    showStatus("weatherStatus", "Notification permission was not granted.", true);
  }
}

async function startCameraPreview() {
  const video = document.getElementById("cameraPreview");
  if (!video || !navigator.mediaDevices?.getUserMedia) {
    showStatus("cameraStatus", "Camera preview is not supported in this browser.", true);
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
    video.srcObject = stream;
    showStatus("cameraStatus", "Camera preview is live. You can now use the try-on simulator with your webcam context.");
  } catch (error) {
    showStatus("cameraStatus", `Camera permission failed: ${error.message}`, true);
  }
}

function captureReferenceFrame() {
  const video = document.getElementById("cameraPreview");
  if (!video || !video.videoWidth || !video.videoHeight) {
    showStatus("cameraStatus", "Start the camera before capturing a reference frame.", true);
    return;
  }
  state.tryOnSnapshot = {
    frame_width: video.videoWidth,
    frame_height: video.videoHeight,
  };
  showStatus("cameraStatus", `Reference frame captured at ${video.videoWidth}x${video.videoHeight}.`);
}

async function refreshState() {
  const [auth, wardrobe, history] = await Promise.all([
    api("/api/auth/status"),
    api("/api/wardrobe"),
    api("/api/outfits/history"),
  ]);
  renderAuth(auth);
  state.wardrobe = wardrobe;
  state.history = history;
  renderWardrobe();
  renderHistory();
  renderOutfitGallery();
}

async function initHome() {
  const summary = await api("/api/platform-summary");
  document.getElementById("heroMetrics").innerHTML = summary.hero_metrics.map(metricCard).join("");
  setLoaded("#heroMetrics");
  renderFeatureGroups(summary.feature_groups);
  renderDiscovery(summary.community_feed);
  activateFeature(location.hash.replace("#", "") || "overview");

  const draftRaw = sessionStorage.getItem("stylesense.tryOnDraft");
  if (draftRaw) {
    try {
      const draft = JSON.parse(draftRaw);
      sessionStorage.removeItem("stylesense.tryOnDraft");
      const tryOnForm = document.getElementById("tryOnForm");
      if (tryOnForm instanceof HTMLFormElement) {
        const assign = (name, value) => {
          const field = tryOnForm.elements.namedItem(name);
          if (field instanceof HTMLInputElement || field instanceof HTMLSelectElement) {
            field.value = value;
          }
        };
        assign("top", draft.top || "");
        assign("bottom", draft.bottom || "");
        assign("avatar", draft.avatar || "StyleSense AI Outfit");
        assign("body_type", draft.body_type || "Personalized");
        assign("fit", draft.fit || "True to size");
        assign("height_cm", String(draft.height_cm || 172));
        assign("shoulder_cm", String(draft.shoulder_cm || 46));
        assign("waist_cm", String(draft.waist_cm || 80));
        assign("inseam_cm", String(draft.inseam_cm || 78));
        assign("camera_distance", draft.camera_distance || "Medium");
        assign("posture", draft.posture || "Neutral");
      }
      const draftResponse = await jsonRequest("/api/try-on", "POST", draft);
      renderTryOn(draftResponse);
      activateFeature("tryon");
    } catch (error) {
      console.error(error);
    }
  }
}

function formToJson(form) {
  return Object.fromEntries(new FormData(form).entries());
}

document.addEventListener("submit", async (event) => {
  const { target } = event;
  if (!(target instanceof HTMLFormElement)) return;

  const handledForms = [
    "recommendForm",
    "tryOnForm",
    "wardrobeForm",
    "chatForm",
    "discoverForm",
    "lookbookForm",
    "loginForm",
    "signupForm",
    "weatherContextForm",
  ];
  if (handledForms.includes(target.id)) {
    event.preventDefault();
  }

  try {
    if (target.id === "recommendForm") {
      const result = await formRequest("/api/recommend", "POST", new FormData(target));
      renderRecommendation(result);
      await refreshState();
    }

    if (target.id === "tryOnForm") {
      const video = document.getElementById("cameraPreview");
      const framePayload =
        state.tryOnSnapshot ||
        (video && video.videoWidth && video.videoHeight
          ? { frame_width: video.videoWidth, frame_height: video.videoHeight }
          : { frame_width: 720, frame_height: 960 });
      renderTryOn(await jsonRequest("/api/try-on", "POST", { ...formToJson(target), ...framePayload }));
    }

    if (target.id === "wardrobeForm") {
      const formData = new FormData(target);
      const image = formData.get("image");
      if (image instanceof File && image.name) {
        await api("/api/wardrobe/upload", { method: "POST", body: formData });
      } else {
        await jsonRequest("/api/wardrobe", "POST", formToJson(target));
      }
      target.reset();
      showStatus("uploadStatus", "Wardrobe item added successfully.");
      await refreshState();
    }

    if (target.id === "chatForm") {
      renderChat(await jsonRequest("/api/chat", "POST", formToJson(target)));
    }

    if (target.id === "discoverForm") {
      const response = await jsonRequest("/api/discover", "POST", formToJson(target));
      renderDiscovery(response.results);
    }

    if (target.id === "lookbookForm") {
      renderLookbook(await jsonRequest("/api/lookbook", "POST", formToJson(target)));
    }

    if (target.id === "weatherContextForm") {
      if (!state.location) {
        showStatus("weatherStatus", "Share your location first so the UI can personalize the report.", true);
      } else {
        const result = await jsonRequest("/api/weather-outfit", "POST", { ...state.location, ...formToJson(target) });
        renderWeatherOutfit(result);
        showStatus("weatherStatus", "Local weather outfit generated.");
        await refreshState();
      }
    }

    if (target.id === "loginForm") {
      renderAuth(await jsonRequest("/api/auth/login", "POST", formToJson(target)));
      target.reset();
      await refreshState();
    }

    if (target.id === "signupForm") {
      renderAuth(await jsonRequest("/api/auth/signup", "POST", formToJson(target)));
      target.reset();
      await refreshState();
    }
  } catch (error) {
    if (target.id === "wardrobeForm") {
      showStatus("uploadStatus", error.message, true);
    }
    if (target.id === "loginForm" || target.id === "signupForm") {
      showStatus("authSummary", error.message, true);
    }
  }
});

document.addEventListener("change", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) return;
  if (target.closest("#recommendForm") && target.name === "reference_image") {
    updateStylistImagePreview(target.files?.[0] || null);
  }
});

document.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;

  const featureLink = target.closest("a[data-section-target]");
  if (featureLink && page === "home") {
    event.preventDefault();
    activateFeature(featureLink.dataset.sectionTarget);
    history.replaceState(null, "", `#${featureLink.dataset.sectionTarget}`);
    return;
  }

  const favoriteId = target.dataset.favoriteId;
  if (favoriteId) {
    await api(`/api/wardrobe/${favoriteId}/favorite`, { method: "POST" });
    await refreshState();
  }

  const tryOnOutfitId = target.dataset.tryonOutfitId;
  if (tryOnOutfitId) {
    const outfit = state.history.find((entry) => entry.id === tryOnOutfitId);
    if (outfit) {
      storeTryOnDraft(outfit);
      if (page === "wardrobe") {
        window.location.href = "/#tryon";
      } else {
        activateFeature("tryon");
        const draft = JSON.parse(sessionStorage.getItem("stylesense.tryOnDraft") || "{}");
        const response = await jsonRequest("/api/try-on", "POST", draft);
        renderTryOn(response);
        sessionStorage.removeItem("stylesense.tryOnDraft");
      }
    }
  }

  const addOutfitId = target.dataset.addOutfitId;
  if (addOutfitId) {
    const outfit = state.history.find((entry) => entry.id === addOutfitId);
    if (outfit) {
      const parsed = parseOutfitItems(outfit);
      await jsonRequest("/api/recommend/save-to-wardrobe", "POST", {
        outfit: {
          name: outfit.name,
          occasion: outfit.occasion,
          weather: outfit.weather,
          top: parsed.top,
          bottom: parsed.bottom,
          shoes: parsed.shoes,
          layer: parsed.layer,
          accessories: parsed.accessories,
          preferred_fabric: outfit.preferred_fabric || "Cotton",
          fabric: outfit.preferred_fabric || "Cotton",
          color: "Neutral",
          pattern: "Solid",
        },
      });
      showStatus("uploadStatus", "Added the full outfit to your wardrobe.");
      await refreshState();
    }
  }

  const deleteId = target.dataset.deleteId;
  if (deleteId) {
    await api(`/api/wardrobe/${deleteId}`, { method: "DELETE" });
    showStatus("uploadStatus", "Wardrobe item deleted.");
    await refreshState();
  }

  if (target.id === "logoutButton") {
    await api("/api/auth/logout", { method: "POST" });
    await refreshState();
  }

  if (target.id === "weatherButton") {
    await requestWeatherOutfitWithLocation(false);
  }

  if (target.id === "notificationButton") {
    await requestNotificationPermission();
  }

  if (target.id === "cameraButton") {
    await startCameraPreview();
  }

  if (target.id === "captureFrameButton") {
    captureReferenceFrame();
  }

  if (target.id === "applyTryOnButton") {
    await tryOnRecommendation();
  }

  if (target.id === "saveRecommendationButton") {
    await saveRecommendationToWardrobe();
  }

  if (target.id === "clearTimelineButton") {
    await api("/api/outfits/history", { method: "DELETE" });
    showStatus("timelineStatus", "Timeline cleared.");
    await refreshState();
  }
});

const themeToggle = document.getElementById("themeToggle");
if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const html = document.documentElement;
    html.dataset.theme = html.dataset.theme === "dark" ? "light" : "dark";
  });
}

window.addEventListener("hashchange", () => {
  if (page === "home") {
    activateFeature(location.hash.replace("#", "") || "overview");
  }
});

(async function init() {
  await refreshState();
  if (page === "home") {
    await initHome();
    if ("Notification" in window && Notification.permission === "granted") {
      await requestWeatherOutfitWithLocation(true);
    }
  }
  if (page === "dashboard") {
    renderAnalytics(await api("/api/analytics"));
  }
})();
