"use client";

import { useEffect, useRef } from "react";

interface Segment {
  cx: number;
  cy: number;
  len: number;
  angle: number;
  vx: number;
  vy: number;
  va: number;
}

export default function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    const N = 18;
    const segments: Segment[] = [];

    function resize() {
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }

    resize();
    window.addEventListener("resize", resize);

    for (let i = 0; i < N; i++) {
      segments.push({
        cx: Math.random() * canvas.width,
        cy: Math.random() * canvas.height,
        len: 30 + Math.random() * 30,
        angle: Math.random() * Math.PI * 2,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        va: (Math.random() - 0.5) * 0.005,
      });
    }

    function draw() {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (const seg of segments) {
        seg.cx += seg.vx;
        seg.cy += seg.vy;
        seg.angle += seg.va;

        if (seg.cx < 0 || seg.cx > canvas.width) seg.vx *= -1;
        if (seg.cy < 0 || seg.cy > canvas.height) seg.vy *= -1;

        const cos = Math.cos(seg.angle);
        const sin = Math.sin(seg.angle);
        const half = seg.len / 2;
        const x1 = seg.cx - cos * half;
        const y1 = seg.cy - sin * half;
        const x2 = seg.cx + cos * half;
        const y2 = seg.cy + sin * half;

        ctx.globalAlpha = 0.2;
        ctx.strokeStyle = "rgba(148, 130, 241, 1)";
        ctx.lineWidth = 1.5;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();

        ctx.globalAlpha = 0.35;
        ctx.fillStyle = "rgba(148, 130, 241, 1)";
        ctx.beginPath();
        ctx.arc(x1, y1, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(x2, y2, 2, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.globalAlpha = 1;
      animId = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
    />
  );
}
