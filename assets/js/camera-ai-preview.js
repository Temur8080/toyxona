const POSE_CONNECTIONS = [
    [0, 1], [0, 2], [1, 3], [2, 4],
    [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
    [5, 11], [6, 12], [11, 12],
    [11, 13], [13, 15], [12, 14], [14, 16],
];

const POSE_COLORS = ["#22d3ee", "#a78bfa", "#34d399", "#fbbf24", "#f87171"];

function normalizePoint(point, width, height) {
    if (!point) return null;

    let x;
    let y;
    let conf = 1;

    if (Array.isArray(point)) {
        x = point[0];
        y = point[1];
        conf = point.length > 2 ? point[2] : 1;
    } else if (typeof point === "object") {
        x = point.x ?? point[0];
        y = point.y ?? point[1];
        conf = point.conf ?? point.score ?? point[2] ?? 1;
    } else {
        return null;
    }

    if (x == null || y == null) return null;

    x = Number(x);
    y = Number(y);
    conf = Number(conf);

    if (Number.isNaN(x) || Number.isNaN(y)) return null;

    if (x > 1 || y > 1) {
        if (x > 1000 || y > 1000) {
            x = x * width / 100000;
            y = y * height / 100000;
        }
    } else {
        x *= width;
        y *= height;
    }

    return {x, y, conf};
}

function extractPersons(payload) {
    if (!payload) return [];

    if (Array.isArray(payload)) {
        if (payload.length && Array.isArray(payload[0])) {
            return payload.map(keypoints => ({keypoints}));
        }
        if (payload.length && payload[0]?.keypoints) {
            return payload;
        }
        return [];
    }

    if (Array.isArray(payload.persons)) return payload.persons;
    if (Array.isArray(payload.people)) return payload.people;
    if (Array.isArray(payload.poses)) return payload.poses;
    if (Array.isArray(payload.results)) return payload.results;

    const nested = [];
    Object.values(payload).forEach(value => {
        if (Array.isArray(value) && value.length && (value[0]?.keypoints || Array.isArray(value[0]))) {
            nested.push(...extractPersons(value));
        }
    });
    return nested;
}

function drawSkeleton(ctx, persons, width, height) {
    persons.forEach((person, index) => {
        const keypoints = person.keypoints || person.points || person.pose || person;
        if (!Array.isArray(keypoints)) return;

        const pts = keypoints.map(point => normalizePoint(point, width, height)).filter(Boolean);
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

        pts.forEach(point => {
            if (point.conf <= 0.2) return;
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(point.x, point.y, 3, 0, Math.PI * 2);
            ctx.fill();
        });
    });
}

function initAiPreview(root, options = {}) {
    const canvas = root.querySelector("canvas");
    const statusEl = root.querySelector("[data-ai-status]");
    const ctx = canvas.getContext("2d");
    let running = true;
    let busy = false;

    async function tick() {
        if (!running || busy) return;
        busy = true;

        const ts = Date.now();
        try {
            const [imageResp, dataResp] = await Promise.all([
                fetch(`${options.imageUrl}?image=true&${ts}`),
                fetch(`${options.dataUrl}?data=true&${ts}`).catch(() => null),
            ]);

            if (!imageResp.ok) throw new Error("image");

            const blob = await imageResp.blob();
            const bitmap = await createImageBitmap(blob);
            canvas.width = bitmap.width;
            canvas.height = bitmap.height;
            ctx.drawImage(bitmap, 0, 0);

            if (dataResp && dataResp.ok) {
                const payload = await dataResp.json();
                const persons = extractPersons(payload);
                if (persons.length) {
                    drawSkeleton(ctx, persons, canvas.width, canvas.height);
                    if (statusEl) {
                        statusEl.textContent = `${persons.length}`;
                    }
                } else if (statusEl) {
                    statusEl.textContent = "AI";
                }
            } else if (statusEl) {
                statusEl.textContent = "AI";
            }
        } catch (error) {
            if (statusEl) statusEl.textContent = "...";
        } finally {
            busy = false;
            if (running) {
                setTimeout(tick, options.interval || 1000);
            }
        }
    }

    tick();

    return () => {
        running = false;
    };
}

if (typeof window !== "undefined") {
    window.initAiPreview = initAiPreview;
}
