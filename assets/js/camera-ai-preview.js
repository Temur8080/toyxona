/**
 * AI preview: asosan Edge /api/ai/snapshot (skeleton rasmda chizilgan).
 * Qo'shimcha: poses JSON bo'lsa canvas ustiga overlay.
 */
const POSE_CONNECTIONS = [
    [0, 1], [0, 2], [1, 3], [2, 4],
    [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
    [5, 11], [6, 12], [11, 12],
    [11, 13], [13, 15], [12, 14], [14, 16],
];

const POSE_COLORS = ["#22d3ee", "#a78bfa", "#34d399", "#fbbf24", "#f87171"];

function parsePoint(point) {
    if (!point) return null;
    if (Array.isArray(point)) {
        return {
            x: Number(point[0]),
            y: Number(point[1]),
            conf: point.length > 2 ? Number(point[2]) : 1,
        };
    }
    if (typeof point === "object") {
        return {
            x: Number(point.x ?? point[0]),
            y: Number(point.y ?? point[1]),
            conf: Number(point.conf ?? point.score ?? point[2] ?? 1),
        };
    }
    return null;
}

function detectCoordMode(points, width, height) {
    let maxX = 0;
    let maxY = 0;
    let minX = Infinity;
    let minY = Infinity;
    for (const p of points) {
        maxX = Math.max(maxX, p.x);
        maxY = Math.max(maxY, p.y);
        minX = Math.min(minX, p.x);
        minY = Math.min(minY, p.y);
    }
    if (maxX <= 1.05 && maxY <= 1.05 && minX >= 0) return "normalized";
    if (maxX <= 100 && maxY <= 100 && minX >= 0) return "percent";
    if (maxX <= width * 1.1 && maxY <= height * 1.1) return "pixels";
    if (maxX > 1000 || maxY > 1000) return "micro";
    return "pixels";
}

function normalizePoint(point, width, height, mode) {
    const raw = parsePoint(point);
    if (!raw || Number.isNaN(raw.x) || Number.isNaN(raw.y)) return null;

    let {x, y, conf} = raw;
    if (mode === "normalized") {
        x *= width;
        y *= height;
    } else if (mode === "percent") {
        x = x * width / 100;
        y = y * height / 100;
    } else if (mode === "micro") {
        x = x * width / 1000;
        y = y * height / 1000;
    }
    return {x, y, conf: Number.isNaN(conf) ? 1 : conf};
}

function extractPersons(payload) {
    if (!payload) return [];

    if (Array.isArray(payload)) {
        if (payload.length && Array.isArray(payload[0])) {
            return payload.map(keypoints => ({keypoints}));
        }
        if (payload.length && payload[0]?.keypoints) return payload;
        return [];
    }

    if (Array.isArray(payload.persons)) return payload.persons;
    if (Array.isArray(payload.people)) return payload.people;
    if (Array.isArray(payload.poses)) return payload.poses;
    if (Array.isArray(payload.results)) return payload.results;
    if (payload.data) return extractPersons(payload.data);

    const nested = [];
    Object.values(payload).forEach(value => {
        if (Array.isArray(value) && value.length) {
            nested.push(...extractPersons(value));
        }
    });
    return nested;
}

function drawSkeleton(ctx, persons, width, height) {
    persons.forEach((person, index) => {
        const keypoints = person.keypoints || person.points || person.pose || person;
        if (!Array.isArray(keypoints) || keypoints.length < 3) return;

        const parsed = keypoints.map(parsePoint).filter(Boolean);
        const mode = detectCoordMode(parsed, width, height);
        const pts = keypoints
            .map(p => normalizePoint(p, width, height, mode))
            .filter(Boolean);
        if (pts.length < 3) return;

        const color = POSE_COLORS[index % POSE_COLORS.length];
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.lineCap = "round";

        POSE_CONNECTIONS.forEach(([a, b]) => {
            const p1 = pts[a];
            const p2 = pts[b];
            if (!p1 || !p2 || p1.conf <= 0.2 || p2.conf <= 0.2) return;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
        });

        pts.forEach(p => {
            if (p.conf <= 0.2) return;
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
            ctx.fill();
        });
    });
}

function initAiPreview(root, options = {}) {
    const img = root.querySelector("[data-ai-img]");
    const canvas = root.querySelector("canvas");
    const statusEl = root.querySelector("[data-ai-status]");
    const ctx = canvas?.getContext("2d");
    const interval = options.interval || 1500;
    let running = true;
    let busy = false;

    async function loadImage(ts) {
        const resp = await fetch(`${options.imageUrl}?image=true&_=${ts}`, {cache: "no-store"});
        if (!resp.ok) throw new Error("image");
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const old = img.dataset.blobUrl;
        img.src = url;
        if (old) URL.revokeObjectURL(old);
        img.dataset.blobUrl = url;
        return blob;
    }

    async function loadOverlay(width, height) {
        if (!canvas || !ctx) return 0;
        const resp = await fetch(`${options.dataUrl}?data=true&_=${Date.now()}`, {cache: "no-store"}).catch(() => null);
        if (!resp || !resp.ok) {
            canvas.style.display = "none";
            return 0;
        }
        const persons = extractPersons(await resp.json());
        if (!persons.length) {
            canvas.style.display = "none";
            return 0;
        }
        canvas.width = width;
        canvas.height = height;
        canvas.style.display = "block";
        ctx.clearRect(0, 0, width, height);
        drawSkeleton(ctx, persons, width, height);
        return persons.length;
    }

    async function tick() {
        if (!running || busy) return;
        busy = true;
        const ts = Date.now();
        try {
            const blob = await loadImage(ts);
            const bitmap = await createImageBitmap(blob);
            const n = await loadOverlay(bitmap.width, bitmap.height);
            if (statusEl) {
                statusEl.textContent = n > 0 ? String(n) : (options.useAi ? "AI" : "…");
            }
        } catch (e) {
            if (statusEl) statusEl.textContent = "…";
        } finally {
            busy = false;
            if (running) setTimeout(tick, interval);
        }
    }

    tick();
    return () => { running = false; };
}

if (typeof window !== "undefined") {
    window.initAiPreview = initAiPreview;
}
