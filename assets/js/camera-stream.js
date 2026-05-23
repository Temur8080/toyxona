/**
 * Live stream — VPS nginx → Edge go2rtc (VPN).
 * WebRTC orqali ikki hop juda qotadi; MSE/MJPEG barqarorroq.
 */
const wsScheme = location.protocol === "https:" ? "wss" : "ws";
let streamHost = document.currentScript?.getAttribute("data-stream-host");

function init_stream(token, container = null) {
    const host = document.querySelector(".video-shell") || container;
    if (!host) return null;

    host.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "w-100";
    host.appendChild(wrap);

    const el = document.createElement("video-stream");
    el.mode = "mse,mjpeg";
    el.media = "video";
    el.background = false;
    el.visibilityCheck = true;

    if (!streamHost || streamHost.length === 0) {
        streamHost = location.host;
    }

    const url = new URL(`${wsScheme}://${streamHost}/camera/stream/`, location.href);
    url.searchParams.set("token", token);
    el.src = url.href;

    const errBox = document.createElement("div");
    errBox.className = "alert alert-danger d-none mt-2 small";
    errBox.setAttribute("role", "alert");
    wrap.appendChild(el);
    wrap.appendChild(errBox);

    const showErr = (msg) => {
        errBox.textContent = msg;
        errBox.classList.remove("d-none");
    };

    el.addEventListener("error", () => showErr(
        "Live stream xato. .env da CONTROL_ACCESS_TOKEN va CAMERA_STREAM_HOST=176.101.56.247 tekshiring; admin da kamera login/parol to'ldirilgan bo'lsin."
    ));

    const obs = new MutationObserver(() => {
        const status = el.querySelector(".status");
        if (status && status.innerText && status.innerText !== "loading" && status.innerText.length > 2) {
            showErr(status.innerText);
        }
    });
    obs.observe(el, {childList: true, subtree: true, characterData: true});

    return el;
}

if (typeof window !== "undefined") {
    window.init_stream = init_stream;
}
