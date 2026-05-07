import { useState, useRef, useEffect, useCallback } from "react";

const SEG_META = {
  video_content: { bg: "#16a34a", text: "#fff", label: "Content" },
  ad:            { bg: "#dc2626", text: "#fff", label: "Ad" },
};

function fmtTime(s) {
  if (!isFinite(s) || s < 0) s = 0;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sc = Math.floor(s % 60);
  return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(sc).padStart(2,"0")}`;
}

function getActiveIdx(segments, t) {
  for (let i = 0; i < segments.length; i++) {
    if (t >= segments[i].final_video_start_seconds && t < segments[i].final_video_end_seconds)
      return i;
  }
  return -1;
}

function getRulerTicks(duration) {
  if (!duration) return [];
  let iv = 5;
  for (const v of [5, 10, 15, 30, 60, 120, 300, 600, 900, 1200]) {
    if (duration / v <= 10) { iv = v; break; }
  }
  const ticks = [];
  for (let t = 0; t <= duration; t += iv) ticks.push(t);
  return ticks;
}

function Timeline({ segments, duration, currentTime, onSeek }) {
  const barRef  = useRef(null);
  const [drag, setDrag] = useState(false);

  const seekFromX = useCallback((clientX) => {
    if (!barRef.current || !duration) return;
    const r = barRef.current.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (clientX - r.left) / r.width));
    onSeek(pct * duration);
  }, [duration, onSeek]);

  useEffect(() => {
    if (!drag) return;
    const mv = (e) => seekFromX(e.clientX);
    const up = () => setDrag(false);
    window.addEventListener("mousemove", mv);
    window.addEventListener("mouseup", up);
    return () => { window.removeEventListener("mousemove", mv); window.removeEventListener("mouseup", up); };
  }, [drag, seekFromX]);

  const ph = duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0;
  const ticks = getRulerTicks(duration);

  return (
    <div style={{ borderTop: "0.5px solid var(--color-border-tertiary)", background: "var(--color-background-secondary)" }}>
      <div
        ref={barRef}
        onMouseDown={(e) => { setDrag(true); seekFromX(e.clientX); }}
        style={{ position: "relative", height: 36, cursor: "crosshair", overflow: "hidden", background: "var(--color-background-tertiary)", userSelect: "none" }}
      >
        {!segments.length && (
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-text-tertiary)", fontSize: 11, fontFamily: "var(--font-mono)" }}>
            Load a JSON file to see segments
          </div>
        )}

        {segments.map((seg, i) => {
          const left  = duration > 0 ? (seg.final_video_start_seconds / duration) * 100 : 0;
          const width = duration > 0 ? ((seg.duration_seconds || 0) / duration) * 100 : 0;
          const m = SEG_META[seg.type] || { bg: "#666", text: "#fff", label: seg.type };
          return (
            <div key={i} style={{
              position: "absolute", left: `${left}%`, width: `${width}%`, top: 0, bottom: 0,
              background: m.bg, overflow: "hidden",
              borderRight: "1px solid rgba(0,0,0,0.25)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 9, fontWeight: 500, color: m.text, fontFamily: "var(--font-mono)",
            }}>
              {width > 4 ? m.label : ""}
            </div>
          );
        })}

        <div style={{ position: "absolute", left: `${ph}%`, top: 0, bottom: 0, width: 2, background: "#f59e0b", transform: "translateX(-1px)", pointerEvents: "none", zIndex: 10 }}>
          <div style={{ position: "absolute", top: 0, left: "50%", transform: "translateX(-50%)", width: 8, height: 8, background: "#f59e0b", borderRadius: "50%" }} />
        </div>
      </div>

      <div style={{ position: "relative", height: 18, overflow: "hidden" }}>
        {ticks.map((t) => (
          <div key={t} style={{ position: "absolute", left: `${(t / duration) * 100}%`, top: 0, bottom: 0, display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
            <div style={{ width: 1, height: 4, background: "var(--color-border-secondary)" }} />
            <span style={{ fontSize: 9, color: "var(--color-text-tertiary)", fontFamily: "var(--font-mono)", whiteSpace: "nowrap", transform: "translateX(-50%)", paddingLeft: 2 }}>
              {fmtTime(t)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SegRow({ seg, index, isActive, onPlay, onSkip }) {
  const m = SEG_META[seg.type] || { bg: "#666", text: "#fff", label: seg.type };
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 6, padding: "5px 8px",
      borderLeft: `3px solid ${isActive ? "#3b82f6" : "transparent"}`,
      background: isActive ? "var(--color-background-info)" : "transparent",
      borderBottom: "0.5px solid var(--color-border-tertiary)",
      transition: "background 0.1s",
    }}>
      <span style={{ background: m.bg, color: m.text, borderRadius: 3, fontSize: 9, fontWeight: 500, padding: "2px 5px", minWidth: 46, textAlign: "center", fontFamily: "var(--font-mono)", flexShrink: 0 }}>
        {m.label}
      </span>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-text-secondary)", lineHeight: 1.5, flexShrink: 0, width: 96 }}>
        <div>{(seg.final_video_start_formatted || "").slice(0,8)}</div>
        <div>{(seg.final_video_end_formatted   || "").slice(0,8)}</div>
      </div>
      <div style={{ flex: 1, fontSize: 10, color: "var(--color-text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {seg.type === "ad"
          ? (seg.ad_filename || `Ad #${index + 1}`)
          : `Segment ${seg.segment_index ?? index}  (${fmtTime(seg.duration_seconds || 0)})`}
      </div>
      <button onClick={() => onPlay(seg.final_video_start_seconds)}
        style={{ fontSize: 9, padding: "3px 6px", background: "#16a34a", color: "#fff", border: "none", borderRadius: 3, cursor: "pointer", whiteSpace: "nowrap", flexShrink: 0 }}>
        ▶ Play
      </button>
      <button onClick={() => onSkip(seg.final_video_end_seconds)}
        style={{ fontSize: 9, padding: "3px 6px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 3, cursor: "pointer", whiteSpace: "nowrap", flexShrink: 0 }}>
        ⏭ Skip
      </button>
    </div>
  );
}

export default function VideoPlayer() {
  const videoRef    = useRef(null);
  const videoInRef  = useRef(null);
  const jsonInRef   = useRef(null);
  const panelRef    = useRef(null);

  const [videoSrc,  setVideoSrc]  = useState(null);
  const [videoName, setVideoName] = useState("");
  const [segments,  setSegments]  = useState([]);
  const [jsonName,  setJsonName]  = useState("");
  const [stats,     setStats]     = useState(null);

  const [playing,   setPlaying]   = useState(false);
  const [curTime,   setCurTime]   = useState(0);
  const [duration,  setDuration]  = useState(0);
  const [volume,    setVolume]    = useState(80);
  const [contOnly,  setContOnly]  = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const [dropping,  setDropping]  = useState(false);

  const loadVideo = (file) => {
    if (!file) return;
    setVideoSrc(URL.createObjectURL(file));
    setVideoName(file.name);
  };

  const loadJson = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);
        const segs = data.timeline_segments || [];
        setSegments(segs);
        setJsonName(file.name);
        const nAds = segs.filter(s => s.type === "ad").length;
        const adDur = segs.filter(s => s.type === "ad").reduce((a, s) => a + (s.duration_seconds || 0), 0);
        setStats({ total: segs.length, nAds, adDur, nContent: segs.filter(s => s.type === "video_content").length });
      } catch { alert("Invalid JSON"); }
    };
    reader.readAsText(file);
  };

  useEffect(() => {
    const vid = videoRef.current;
    if (!vid) return;

    const onTime = () => {
      setCurTime(vid.currentTime);
      const idx = getActiveIdx(segments, vid.currentTime);
      setActiveIdx(idx);
      if (contOnly && idx >= 0 && segments[idx]?.type === "ad") {
        vid.currentTime = segments[idx].final_video_end_seconds;
      }
    };
    const onDur  = () => setDuration(vid.duration || 0);
    const onPlay = () => setPlaying(true);
    const onPause= () => setPlaying(false);

    vid.addEventListener("timeupdate", onTime);
    vid.addEventListener("durationchange", onDur);
    vid.addEventListener("play", onPlay);
    vid.addEventListener("pause", onPause);
    vid.addEventListener("ended", onPause);
    return () => {
      vid.removeEventListener("timeupdate", onTime);
      vid.removeEventListener("durationchange", onDur);
      vid.removeEventListener("play", onPlay);
      vid.removeEventListener("pause", onPause);
      vid.removeEventListener("ended", onPause);
    };
  }, [segments, contOnly]);

  useEffect(() => { if (videoRef.current) videoRef.current.volume = volume / 100; }, [volume]);

  const seekTo = useCallback((s) => {
    const vid = videoRef.current;
    if (vid) vid.currentTime = Math.max(0, Math.min(s, vid.duration || 0));
  }, []);

  const togglePlay = useCallback(() => {
    const vid = videoRef.current;
    if (!vid || !videoSrc) return;
    playing ? vid.pause() : vid.play();
  }, [playing, videoSrc]);

  const stop = useCallback(() => {
    const vid = videoRef.current;
    if (vid) { vid.pause(); vid.currentTime = 0; }
  }, []);

  const prevSeg = useCallback(() => {
    if (!segments.length) return;
    seekTo(segments[Math.max(0, activeIdx - 1)].final_video_start_seconds);
  }, [segments, activeIdx, seekTo]);

  const nextSeg = useCallback(() => {
    if (!segments.length) return;
    seekTo(segments[Math.min(segments.length - 1, activeIdx + 1)].final_video_start_seconds);
  }, [segments, activeIdx, seekTo]);

  const skipAd = useCallback(() => {
    if (activeIdx >= 0 && segments[activeIdx]?.type === "ad")
      seekTo(segments[activeIdx].final_video_end_seconds);
  }, [segments, activeIdx, seekTo]);

  useEffect(() => {
    const h = (e) => {
      if (e.target.tagName === "INPUT") return;
      if (e.key === " ") { e.preventDefault(); togglePlay(); }
      else if (e.key === "s" || e.key === "S") stop();
      else if (e.key === "ArrowLeft")  { e.preventDefault(); seekTo(curTime - 5); }
      else if (e.key === "ArrowRight") { e.preventDefault(); seekTo(curTime + 5); }
      else if (e.key === "[") prevSeg();
      else if (e.key === "]") nextSeg();
      else if (e.key === "a" || e.key === "A") skipAd();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [togglePlay, stop, seekTo, prevSeg, nextSeg, skipAd, curTime]);

  useEffect(() => {
    if (activeIdx < 0 || !panelRef.current) return;
    const rows = panelRef.current.querySelectorAll("[data-seg-row]");
    rows[activeIdx]?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeIdx]);

  const handleDrop = (e) => {
    e.preventDefault(); setDropping(false);
    for (const f of e.dataTransfer.files) {
      if (f.name.endsWith(".json")) loadJson(f);
      else if (f.type.startsWith("video/")) loadVideo(f);
    }
  };

  const curSeg = activeIdx >= 0 ? segments[activeIdx] : null;
  const isInAd = curSeg?.type === "ad";

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDropping(true); }}
      onDragLeave={() => setDropping(false)}
      onDrop={handleDrop}
      style={{
        border: dropping ? "2px dashed #f59e0b" : "0.5px solid var(--color-border-tertiary)",
        borderRadius: "var(--border-radius-lg)",
        overflow: "hidden",
        background: "var(--color-background-secondary)",
        fontFamily: "var(--font-sans)",
      }}
    >
      <input ref={videoInRef} type="file" accept="video/*" style={{ display: "none" }} onChange={e => loadVideo(e.target.files[0])} />
      <input ref={jsonInRef}  type="file" accept=".json"  style={{ display: "none" }} onChange={e => loadJson(e.target.files[0])} />

      {/* Top bar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", background: "var(--color-background-tertiary)", borderBottom: "0.5px solid var(--color-border-tertiary)", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, overflow: "hidden" }}>
          <span style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {videoName || "No video loaded"}
          </span>
          {jsonName && (
            <span style={{ fontSize: 10, color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)", flexShrink: 0 }}>
              · {jsonName}
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
          <button onClick={() => videoInRef.current.click()} style={{ fontSize: 11, padding: "4px 10px" }}>Open Video</button>
          <button onClick={() => jsonInRef.current.click()}  style={{ fontSize: 11, padding: "4px 10px" }}>Open JSON</button>
        </div>
      </div>

      {/* Main: video + panel */}
      <div style={{ display: "flex", height: 400 }}>
        {/* Video */}
        <div style={{ flex: 1, background: "#000", position: "relative", display: "flex", alignItems: "center", justifyContent: "center", minWidth: 0 }}>
          <video ref={videoRef} src={videoSrc || undefined} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
          {!videoSrc && (
            <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10, color: "#333" }}>
              <div style={{ fontSize: 40, lineHeight: 1 }}>▶</div>
              <div style={{ fontSize: 12, fontFamily: "var(--font-mono)" }}>Drop an MP4 here or click Open Video</div>
            </div>
          )}

          {isInAd && (
            <div style={{ position: "absolute", top: 10, right: 10, background: "#dc2626", color: "#fff", padding: "4px 10px", borderRadius: 4, fontSize: 11, fontWeight: 500, display: "flex", alignItems: "center", gap: 6 }}>
              AD
              <button onClick={skipAd} style={{ background: "rgba(255,255,255,0.2)", border: "none", color: "#fff", fontSize: 10, padding: "2px 6px", borderRadius: 3, cursor: "pointer" }}>
                Skip ⏭
              </button>
            </div>
          )}
        </div>

        {/* Segment panel */}
        <div style={{ width: 300, borderLeft: "0.5px solid var(--color-border-tertiary)", display: "flex", flexDirection: "column", background: "var(--color-background-primary)", flexShrink: 0 }}>
          <div style={{ padding: "8px 10px", borderBottom: "0.5px solid var(--color-border-tertiary)", background: "var(--color-background-secondary)" }}>
            <div style={{ fontSize: 11, fontWeight: 500, color: "var(--color-text-primary)", marginBottom: 3 }}>Segment Overview</div>
            {stats ? (
              <div style={{ fontSize: 10, color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)" }}>
                {stats.total} total · {stats.nContent} content · {stats.nAds} ads ({fmtTime(stats.adDur)})
              </div>
            ) : (
              <div style={{ fontSize: 10, color: "var(--color-text-tertiary)" }}>No segments loaded</div>
            )}
          </div>

          <div ref={panelRef} style={{ flex: 1, overflowY: "auto" }}>
            {segments.map((seg, i) => (
              <div key={i} data-seg-row="">
                <SegRow seg={seg} index={i} isActive={i === activeIdx} onPlay={seekTo} onSkip={seekTo} />
              </div>
            ))}
            {!segments.length && (
              <div style={{ padding: 20, textAlign: "center", color: "var(--color-text-tertiary)", fontSize: 12 }}>
                Load a JSON file to see segments
              </div>
            )}
          </div>

          {curSeg && (
            <div style={{ padding: "6px 10px", borderTop: "0.5px solid var(--color-border-tertiary)", background: "var(--color-background-secondary)", fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)" }}>
              <span style={{ color: SEG_META[curSeg.type]?.bg || "#888", fontWeight: 500 }}>
                {SEG_META[curSeg.type]?.label || curSeg.type}
              </span>
              {"  "}{(curSeg.final_video_start_formatted||"").slice(0,8)} → {(curSeg.final_video_end_formatted||"").slice(0,8)}
            </div>
          )}
        </div>
      </div>

      {/* Timeline */}
      <Timeline segments={segments} duration={duration} currentTime={curTime} onSeek={seekTo} />

      {/* Controls */}
      <div style={{ padding: "8px 12px", background: "var(--color-background-tertiary)", borderTop: "0.5px solid var(--color-border-tertiary)" }}>
        {/* Seek */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)", minWidth: 60 }}>{fmtTime(curTime)}</span>
          <input type="range" min="0" max={duration || 0} step="0.1" value={curTime}
            onChange={e => seekTo(parseFloat(e.target.value))} style={{ flex: 1 }} />
          <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)", minWidth: 60, textAlign: "right" }}>{fmtTime(duration)}</span>
        </div>

        {/* Buttons */}
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <button onClick={togglePlay} title="Play/Pause (Space)" style={{ minWidth: 38, fontSize: 14, padding: "4px 8px" }}>
            {playing ? "⏸" : "▶"}
          </button>
          <button onClick={stop} title="Stop (S)" style={{ fontSize: 12, padding: "4px 8px" }}>■</button>
          <button onClick={prevSeg} title="Prev segment ([)" style={{ fontSize: 11, padding: "4px 8px" }}>⏮ Prev</button>
          <button onClick={nextSeg} title="Next segment (])" style={{ fontSize: 11, padding: "4px 8px" }}>Next ⏭</button>

          <button onClick={skipAd} disabled={!isInAd} title="Skip current ad (A)"
            style={{ fontSize: 11, padding: "4px 10px", background: isInAd ? "#dc2626" : undefined, color: isInAd ? "#fff" : undefined, border: isInAd ? "none" : undefined, opacity: isInAd ? 1 : 0.45, cursor: isInAd ? "pointer" : "default" }}>
            ⏭ Skip Ad
          </button>

          <div style={{ flex: 1 }} />

          <button onClick={() => setContOnly(v => !v)} title="Auto-skip all ads"
            style={{ fontSize: 11, padding: "4px 10px", background: contOnly ? "#16a34a" : undefined, color: contOnly ? "#fff" : undefined, border: contOnly ? "none" : undefined }}>
            {contOnly ? "✓ Content Only" : "Content Only"}
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 12, lineHeight: 1 }}>🔊</span>
            <input type="range" min="0" max="100" step="1" value={volume}
              onChange={e => setVolume(Number(e.target.value))} style={{ width: 72 }} />
            <span style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)", minWidth: 28 }}>{volume}%</span>
          </div>
        </div>

        <div style={{ marginTop: 6, fontSize: 10, color: "var(--color-text-tertiary)", fontFamily: "var(--font-mono)" }}>
          Space play/pause · S stop · ← → ±5s · [ ] segments · A skip ad · drag &amp; drop MP4/JSON
        </div>
      </div>
    </div>
  );
}
