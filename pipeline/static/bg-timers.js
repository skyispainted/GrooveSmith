/* Background-safe timers.
 *
 * Why this file exists
 * --------------------
 * Chrome (88+) throttles main-thread timers in a HIDDEN tab to about once per second,
 * and to about once per minute after five minutes hidden. See
 * https://developer.chrome.com/blog/timer-throttling-in-chrome-88
 *
 * <midi-player> (html-midi-player / @magenta/music) drives its note scheduler from
 * exactly those timers, so MIDI playback starves the moment the tab is backgrounded
 * -- which is why the synthesised drums stop while the <audio> element keeps going.
 *
 * Design (both halves are needed):
 *   - the HEARTBEAT must come from a Web Worker: worker timers are not subject to the
 *     hidden-tab cap, whereas a native setTimeout driving this loop would itself be
 *     throttled to 1/s and defeat the whole thing.
 *   - the CLOCK is the AudioContext, which keeps advancing while audio renders, so
 *     callbacks fire at the right times rather than bunched at the heartbeat.
 * Same combination as chrisguttandin's worker-timers + audio-context-timers.
 *
 * Must load BEFORE midi-player.js so the player picks up the shim.
 * Every call falls back to the native timer while the context is not running (before
 * the first user gesture, or if Web Audio is unavailable), so nothing changes until
 * audio is actually playing.
 */
(function () {
  "use strict";

  var AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;                       // no Web Audio -> leave timers alone

  var ownCtx;
  try { ownCtx = new AC(); } catch (e) { return; }
  if (!ownCtx) return;

  // Prefer the page's own AudioContext once Tone.js has made one: that is the context
  // actually rendering the drum samples, so its clock is certainly advancing.
  function ctx() {
    try {
      if (window.Tone && window.Tone.getContext) {
        var raw = window.Tone.getContext().rawContext;
        if (raw && typeof raw.currentTime === "number") return raw;
      }
    } catch (e) {}
    return ownCtx;
  }

  var nativeSet = window.setTimeout.bind(window);
  var nativeClear = window.clearTimeout.bind(window);

  var seq = 0;
  var tasks = Object.create(null);       // ourId -> {fn, args, due, interval}
  var live = false;

  function pump() {
    var c = ctx();
    if (c.state !== "running") {
      live = false;                      // inert: callers use native timers
      if (!beat) nativeSet(pump, 50);
      return;
    }
    live = true;
    var t = c.currentTime * 1000;
    for (var id in tasks) {
      var task = tasks[id];
      if (task.due <= t) {
        if (task.interval) { task.due = t + task.interval; }
        else { delete tasks[id]; }
        try {
          task.fn.apply(null, task.args);
        } catch (err) {
          nativeSet(function () { throw err; }, 0);   // surface without killing the pump
        }
      }
    }
    if (!beat) nativeSet(pump, 10);
  }

  // Heartbeat. Without it the pump would be a throttled main-thread timer, which is
  // precisely the problem this file exists to solve.
  var beat = null;
  try {
    var src = "setInterval(function(){postMessage(0);},10);";
    beat = new Worker(URL.createObjectURL(new Blob([src], { type: "text/javascript" })));
    beat.onmessage = pump;
  } catch (e) {
    beat = null;                         // fall back to self-scheduling below
  }
  pump();

  // Resume on any user gesture: without one the context stays suspended and the shim
  // stays inert (falling back to native timers, i.e. exactly today's behaviour).
  function arm() {
    [ctx(), ownCtx].forEach(function (c) {
      if (c && c.state === "suspended") { try { c.resume(); } catch (e) {} }
    });
  }
  ["pointerdown", "keydown", "touchstart"].forEach(function (ev) {
    window.addEventListener(ev, arm, true);
  });

  window.setTimeout = function (fn, ms) {
    if (typeof fn !== "function" || !live) return nativeSet.apply(null, arguments);
    var id = "bg" + (++seq);
    tasks[id] = { fn: fn, args: Array.prototype.slice.call(arguments, 2),
                  due: ctx().currentTime * 1000 + (ms || 0) };
    return id;
  };

  window.setInterval = function (fn, ms) {
    if (typeof fn !== "function" || !live) return nativeSet.apply(null, arguments);
    var period = Math.max(1, ms || 0);
    var id = "bg" + (++seq);
    tasks[id] = { fn: fn, args: Array.prototype.slice.call(arguments, 2),
                  due: ctx().currentTime * 1000 + period, interval: period };
    return id;
  };

  window.clearTimeout = function (id) {
    if (typeof id === "string" && tasks[id]) { delete tasks[id]; return; }
    return nativeClear.apply(null, arguments);
  };
  window.clearInterval = window.clearTimeout;
})();
