import { useEffect, useRef } from 'react';

/**
 * AuraVisualizer
 * Props:
 *   audioTrack  – LiveKit audio track object (or null when idle)
 *   speaking    – boolean: true when the agent is currently speaking
 *   color       – ring colour (default cyan)
 */
export default function AuraVisualizer({ audioTrack, speaking, color = "#1FD5F9" }) {
    const canvasRef = useRef(null);   // reference to the <canvas> element
    const animRef = useRef(null);   // stores the requestAnimationFrame ID
    const analyserRef = useRef(null);   // the Web Audio AnalyserNode
    const audioCtxRef = useRef(null);   // the AudioContext

    // ── Wire up Web Audio API when an audio track arrives ────────────
    useEffect(() => {
        if (!audioTrack || !audioTrack.mediaStreamTrack) {
            // No live audio track → just run the idle animation
            startDraw();
            return () => cancelAnimationFrame(animRef.current);
        }

        // Wrap the LiveKit track in a MediaStream the browser understands
        const mediaStream = new MediaStream([audioTrack.mediaStreamTrack]);

        // AudioContext = the browser's audio processing engine
        const ctx = new AudioContext();

        // MediaStreamSource = "plug" the audio stream into the engine
        const source = ctx.createMediaStreamSource(mediaStream);

        // AnalyserNode = reads frequency data without changing the sound
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 256;  // how detailed the frequency analysis is
        source.connect(analyser); // plug source → analyser

        audioCtxRef.current = ctx;
        analyserRef.current = analyser;

        startDraw();

        // cleanup: runs when the component unmounts or audioTrack changes
        return () => {
            cancelAnimationFrame(animRef.current);
            source.disconnect();
            ctx.close();
            analyserRef.current = null;
        };
    }, [audioTrack]); // re-run this effect whenever audioTrack changes

    // ── Also restart draw when speaking state changes (for idle breath) ──
    useEffect(() => {
        if (!audioTrack) {
            startDraw();
            return () => cancelAnimationFrame(animRef.current);
        }
    }, [speaking]);

    // ── The drawing loop ──────────────────────────────────────────────
    function startDraw() {
        cancelAnimationFrame(animRef.current); // cancel any previous loop first

        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx2d = canvas.getContext('2d');  // 2D drawing context
        const cx = canvas.width / 2;          // center X
        const cy = canvas.height / 2;          // center Y

        // Frequency data buffer — 128 numbers (0–255 each)
        const dataArray = new Uint8Array(analyserRef.current?.frequencyBinCount || 128);

        // The 4 concentric rings (innermost to outermost)
        const rings = [
            { baseR: 52, strokeBase: 1.5, opacityBase: 0.15 },
            { baseR: 72, strokeBase: 1.2, opacityBase: 0.12 },
            { baseR: 92, strokeBase: 1.0, opacityBase: 0.09 },
            { baseR: 115, strokeBase: 0.8, opacityBase: 0.06 },
        ];

        let tick = 0; // frame counter — used for sin() wave animations

        function draw() {
            // requestAnimationFrame = browser calls this ~60 times per second
            animRef.current = requestAnimationFrame(draw);
            tick++;

            // Clear the canvas each frame (otherwise drawings stack up)
            ctx2d.clearRect(0, 0, canvas.width, canvas.height);

            // ── Read audio energy ────────────────────────────────────
            let energy = 0;
            if (analyserRef.current) {
                analyserRef.current.getByteFrequencyData(dataArray);
                // Average the first 60 frequency bins (bass/mid range)
                // Divide by 255 to normalise to 0.0–1.0
                energy = dataArray.slice(0, 60).reduce((sum, v) => sum + v, 0) / (60 * 255);
            }

            // ── Calculate visual level ───────────────────────────────
            // Idle: gentle sine wave "breathing" (0.0 → 0.3)
            const breath = (Math.sin(tick * 0.03) * 0.5 + 0.5) * 0.3;
            // Speaking: use real audio energy, minimum 0.15 so it's always visible
            const level = speaking ? Math.max(energy * 2, 0.15) : breath;

            // ── Draw each ring ───────────────────────────────────────
            rings.forEach(({ baseR, strokeBase, opacityBase }, i) => {
                // Phase offset per ring so they don't all pulse identically
                const phase = tick * 0.04 + i * 0.5;
                // How much extra radius to add based on audio energy
                const ripple = level * 18 * (1 - i * 0.15);
                // Final radius = base + audio ripple + gentle sine wobble
                const r = baseR + ripple + Math.sin(phase) * 4;
                // Opacity increases with energy
                const opacity = Math.min(opacityBase + level * (0.7 - i * 0.1), 0.95);
                // Stroke width increases with energy
                const stroke = strokeBase + level * 2.5;

                // Draw the main bright ring
                ctx2d.beginPath();
                ctx2d.arc(cx, cy, r, 0, Math.PI * 2);
                ctx2d.strokeStyle = color;
                ctx2d.globalAlpha = opacity;
                ctx2d.lineWidth = stroke;
                ctx2d.stroke();

                // Draw a wider, dimmer glow ring just outside
                ctx2d.beginPath();
                ctx2d.arc(cx, cy, r + stroke + 2, 0, Math.PI * 2);
                ctx2d.strokeStyle = color;
                ctx2d.globalAlpha = Math.min(opacity * 0.3, 0.4);
                ctx2d.lineWidth = stroke * 3;
                ctx2d.stroke();
            });

            // Reset globalAlpha so future draws aren't affected
            ctx2d.globalAlpha = 1;
        }

        draw(); // kick off the loop
    }

    return (
        <canvas
            ref={canvasRef}
            width={280}
            height={280}
            style={{ position: 'absolute', inset: 0 }}
        />
    );
}
