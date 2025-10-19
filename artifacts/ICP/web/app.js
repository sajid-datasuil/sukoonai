(() => {
  const $ = (s) => document.querySelector(s);
  const on = (el, ev, fn) => { if (el) el.addEventListener(ev, fn, false); };

  function guardPrefix(lang, script){
    if (lang==='en') return 'Please answer strictly in English.\n\n';
    if (lang==='ur' && script==='roman') return 'Meharbani se jawab Roman Urdu mein likhein.\n\n';
    if (lang==='ur' && script==='arabic') return 'براہ کرم جواب اردو رسم الخط میں دیں۔\n\n';
    return '';
  }
  function toMediaUrl(ttsPath){
    if(!ttsPath) return null;
    if(ttsPath.startsWith('artifacts/')) return '/media/' + ttsPath.replace(/^artifacts\\?/,'').replace(/^artifacts\//,'');
    return ttsPath;
  }

  // --- A2 helpers (parity + breadcrumb) ---
  function canonicalAnswer(data){
    // Single canonical string used for BOTH on-screen text and caption:
    // priority: answer_tts → tts_text → answer → text → answer_for_tts
    return (
      data?.answer_tts ??
      data?.tts_text ??
      data?.answer ??
      data?.text ??
      data?.answer_for_tts ??
      ''
    );
  }

  function formatBreadcrumb(data){
    const bits = [];
    if (data?.route) bits.push(`route=${data.route}`);

    // timing (prefer timings.total_ms, else metrics.total_ms, else latency_ms)
    const totalMs =
      data?.timings?.total_ms ??
      data?.metrics?.total_ms ??
      data?.latency_ms ??
      null;
    if (typeof totalMs === 'number' && isFinite(totalMs)) {
      const secs = Math.max(0, totalMs) / 1000;
      bits.push(`t=${secs.toFixed(1)}s`);
    }

    // cost (prefer cost_pkr → cost_pk → usage.cost_pkr → usage.cost_pk)
    const cost =
      data?.cost_pkr ??
      data?.cost_pk ??
      data?.usage?.cost_pkr ??
      data?.usage?.cost_pk ??
      null;
    if (typeof cost === 'number' && isFinite(cost)) {
      bits.push(`cost=₨${cost.toFixed(2)}`);
    }

    return bits.length ? `<div class="muted breadcrumb">${bits.join(' • ')}</div>` : '';
  }

  // --- A3: status ribbon + chips ---
  function fmtLocal(iso){
    try {
      const d = new Date(iso);
      const pad = (n)=> String(n).padStart(2,'0');
      return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    } catch { return ''; }
  }
  function renderRibbon(text){
    const ribbon = `<div class="ribbon muted">${text}</div>`;
    const t = document.querySelector('#text-transcript');
    const v = document.querySelector('#voice-transcript');
    if (t && !t.querySelector('.ribbon')) t.insertAdjacentHTML('afterbegin', ribbon);
    if (v && !v.querySelector('.ribbon')) v.insertAdjacentHTML('afterbegin', ribbon);
  }
  async function initStatus(){
    try{
      const r = await fetch('/api/status');
      const data = await r.json();
      const iso = (data && (data.time_utc || data.time || data.now)) || null;
      const id  = (data && (data.server_id || data.instance_id || data.node_id)) || null;
      const local = iso ? fmtLocal(iso) : 'n/a';
      renderRibbon(`server_time=${local}` + (id ? ` • server_id=${id}` : ''));
    }catch{
      renderRibbon(`server_time=n/a`);
    }
  }
  function chip(outEl, msg){
    if(outEl){ outEl.innerHTML += `<div class="chip error">error=${msg}</div>`; }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const tabText  = $('#tab-text');
    const tabVoice = $('#tab-voice');
    const paneText = $('#pane-text');
    const paneVoice= $('#pane-voice');

    function activate(which){
      if(!tabText || !tabVoice || !paneText || !paneVoice) return;
      if(which === 'text'){
        tabText.classList.add('active'); tabText.setAttribute('aria-selected','true');
        tabVoice.classList.remove('active'); tabVoice.setAttribute('aria-selected','false');
        paneText.classList.remove('hidden'); paneVoice.classList.add('hidden');
      }else{
        tabVoice.classList.add('active'); tabVoice.setAttribute('aria-selected','true');
        tabText.classList.remove('active'); tabText.setAttribute('aria-selected','false');
        paneVoice.classList.remove('hidden'); paneText.classList.add('hidden');
      }
    }
    on(tabText,  'click', () => activate('text'));
    on(tabVoice, 'click', () => activate('voice'));

    // Initialize A3 ribbon
    initStatus();

    // Text options
    const textOptsToggle = $('#text-opts-toggle');
    const textOpts = $('#text-opts');
    on(textOptsToggle, 'click', () => {
      const nowOpen = textOpts.classList.toggle('hidden') === false;
      textOptsToggle.setAttribute('aria-expanded', nowOpen ? 'true' : 'false');
    });

    // ===== Text Chat =====
    const textLangCombo = $('#text-lang-combo'); // 'en:roman' | 'ur:roman' | 'ur:arabic'
    const textInput  = $('#text-input');
    const textSend   = $('#text-send');
    const textOut    = $('#text-transcript');

    function parseCombo(val){
      const [lang, script] = (val || 'en:roman').split(':');
      return { lang: lang || 'en', script: script || 'roman' };
    }

    async function sendText(){
      const raw = (textInput?.value || '').trim();
      if(!raw) return;

      const { lang, script } = parseCombo(textLangCombo?.value);

      const payload = {
        text: guardPrefix(lang, script) + raw,
        mode: "text",
        ui_lang: lang,
        ui_script: script,
        ui_auto: false
      };

      if (textOut) textOut.innerHTML += `<div><b>You:</b> ${raw}</div>`;
      textOut?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' });

      if (lang==='en' && /[\u0600-\u06FF]/.test(raw)) {
        textOut && (textOut.innerHTML += `<div class="muted">Note: You’re set to English. I’ll reply in English.</div>`);
      }
      if (textInput) textInput.value = '';

      try{
        const r = await fetch('/api/web/turn', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(payload)
        });

        if (!r.ok){
          chip(textOut, `HTTP_${r.status}`);
          return;
        }

        const data = await r.json();
        const answer = (data && data.answer) || JSON.stringify(data);
        if (textOut) textOut.innerHTML += `<div><b>SukoonAI:</b> ${answer}</div>`;
        textOut?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }catch(e){
        chip(textOut, 'network');
        textOut?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }
    }
    on(textSend, 'click', sendText);
    on(textInput, 'keydown', (e)=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); sendText(); } });

    // ----- Voice options toggle -----
    const voiceOptsToggle = $('#voice-opts-toggle');
    const voiceOpts = $('#voice-opts');
    on(voiceOptsToggle, 'click', () => {
      const nowOpen = voiceOpts.classList.toggle('hidden') === false;
      voiceOptsToggle.setAttribute('aria-expanded', nowOpen ? 'true' : 'false');
    });

    // ===== Voice Chat =====
    const voiceLang = $('#voice-lang');
    const micBtn    = $('#mic-btn');
    const stopBtn   = $('#stop-btn');
    const vu        = $('#vu');
    const vOut      = $('#voice-transcript');

    let mediaStream = null, mediaRec = null, chunks = [], isRecording = false, levelTimer = null;
    let minStopAt = 0;                 // enforce minimum capture time (A1)
    let scheduledStopTimer = null;     // debounce early Stop (A1)
    let handledStop = false;           // HARD GUARD: ensure onstop path runs once (A1)
    let turnBusy = false;              // block starting another recording while posting previous (A1)

    function currentVoiceLangHint(){
      const v = voiceLang?.value || 'en';
      return { lang: v, stt_hint: v };
    }
    function setSpinner(on){
      if(!vOut) return;
      if(on){ if(!document.querySelector('#__spin')) vOut.innerHTML += `<div id="__spin" class="spinner">Working…</div>`; }
      else { document.querySelector('#__spin')?.remove(); }
    }
    function killAudioBars() {
      // stop any existing audio & remove the bars (single-audio invariant)
      (vOut?.querySelectorAll('audio') || []).forEach(a => { try{ a.pause(); a.currentTime = 0; }catch{} });
      (vOut?.querySelectorAll('.audio-bar') || []).forEach(el => el.remove());
    }

    async function startRecording(){
      if(isRecording || turnBusy) return; // don't start if the previous turn is still posting
      // proactively stop any leftover audio UI
      killAudioBars();

      try{
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio:true });
      }catch(err){
        vOut && (vOut.innerHTML += `<div class="err">Mic error: ${err?.message||err}</div>`);
        return;
      }
      chunks = [];
      handledStop = false;            // reset per turn
      scheduledStopTimer = null;

      try{ mediaRec = new MediaRecorder(mediaStream, { mimeType: 'audio/webm' }); }
      catch{ mediaRec = new MediaRecorder(mediaStream); }

      mediaRec.ondataavailable = (e)=> { if(e.data && e.data.size>0) chunks.push(e.data); };

      mediaRec.onstop = async ()=>{
        // HARD GUARD: prevent duplicate network posts and duplicate UI insertion
        if (handledStop) return;
        handledStop = true;

        try {
          turnBusy = true;
          setSpinner(true);
          const blob = new Blob(chunks, { type: mediaRec.mimeType || 'audio/webm' });
          const fd = new FormData();
          const hint = currentVoiceLangHint();
          fd.append('mode', 'voice');
          fd.append('ui_lang', hint.lang);     // 'en' | 'ur'
          fd.append('audio', blob, 'recording.webm');

          const r = await fetch('/api/web/turn', { method:'POST', body: fd });

          if (!r.ok){
            chip(vOut, `HTTP_${r.status}`);
            return;
          }

          const data = await r.json();

          if (data?.stt_text) {
            vOut && (vOut.innerHTML += `<div><b>You (voice):</b> ${data.stt_text}</div>`);
          }

          // A2: canonical one-source text used for BOTH on-screen text and the audio caption
          const answer = canonicalAnswer(data);

          // Prefer tts_url; fallback to /media/... from tts_path; cache-bust once if missing
          let tts = data?.tts_url || toMediaUrl(data?.tts_path);
          if (tts && !/\?v=/.test(tts)) tts += `?v=${Date.now()}`;

          // Assistant parity line
          if (vOut) {
            vOut.innerHTML += `<div class="assistant-turn"><b>SukoonAI:</b> ${answer || '(no text)'}</div>`;
            // Breadcrumb (route • timing • cost) — silently omit missing fields
            vOut.innerHTML += formatBreadcrumb(data);
          }

          if(tts){
            killAudioBars();

            const id = `audio_${Date.now()}`;
            vOut && (vOut.innerHTML += `
              <div class="audio-bar">
                <span class="caption">Now Playing — ${answer || '…'}</span>
                <audio id="${id}" controls autoplay src="${tts}"></audio>
                <button class="btn light" onclick="document.getElementById('${id}').currentTime=0;document.getElementById('${id}').play()">Replay</button>
              </div>`);

            vOut?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' });

            setTimeout(() => {
              const aud = document.getElementById(id);
              if (!aud) return;
              const bar = aud.closest('.audio-bar');
              const cap = bar?.querySelector('.caption');
              const baseUrl = (aud.src||'').split('?')[0];

              // pace
              try { aud.playbackRate = 0.92; } catch {}
              if (aud.paused) { aud.play().catch(()=>{}); }

              // A3: audio error handler → muted note + Retry (cache-buster)
              aud.onerror = () => {
                if (cap) cap.textContent = '(audio unavailable; text shown)';
                let retryBtn = bar?.querySelector('.retry-btn');
                if (!retryBtn) {
                  retryBtn = document.createElement('button');
                  retryBtn.className = 'btn light retry-btn';
                  retryBtn.textContent = 'Retry audio';
                  retryBtn.onclick = () => {
                    aud.src = `${baseUrl}?retry=${Date.now()}`;
                    aud.play().catch(()=>{ /* keep note; user can retry again */ });
                  };
                  bar?.appendChild(retryBtn);
                }
              };

              // If it later loads, keep playing (caption can stay as "Now Playing")
              aud.oncanplay = () => { /* no-op */ };
            }, 250);
          } else {
            // No audio returned: keep assistant text and show muted note
            vOut && (vOut.innerHTML += `<div class="muted">(no audio returned; text shown)</div>`);
            vOut?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' });
          }
        } catch(e){
          chip(vOut, 'network');
          vOut?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' });
        } finally {
          setSpinner(false);
          turnBusy = false;
        }
      };

      mediaRec.start(250);            // chunk every 250ms
      isRecording = true;
      minStopAt = Date.now() + 1200;  // ≥1.2s minimum capture
      vu?.classList.add('active');
      if (micBtn) micBtn.disabled = true;
      if (stopBtn) stopBtn.disabled = false;

      // tiny shimmer
      let dir=1, w=10;
      levelTimer = setInterval(()=>{
        w += dir*6; if(w>100){w=100; dir=-1;} if(w<10){w=10; dir=1;}
        if (vu) vu.style.background = `linear-gradient(90deg,#e6f3ff,#c4e6ff ${w}%)`;
      }, 90);
    }

    async function stopRecording(){
      if(!isRecording) return;

      const waitMs = minStopAt - Date.now();

      // Debounce: only one scheduled stop
      if (waitMs > 0) {
        if (!scheduledStopTimer) {
          if (stopBtn) stopBtn.disabled = true; // show that stop is armed
          scheduledStopTimer = setTimeout(() => {
            scheduledStopTimer = null;
            stopRecording();
          }, waitMs);
        }
        return;
      }

      try{ mediaRec?.stop(); }catch{}
      mediaStream?.getTracks()?.forEach(t=>t.stop());
      clearInterval(levelTimer); levelTimer=null;
      vu?.classList.remove('active');
      isRecording = false;
      if (micBtn) micBtn.disabled = false;
      if (stopBtn) stopBtn.disabled = true;
    }

    on(micBtn,  'click', startRecording);
    on(stopBtn, 'click', stopRecording);
  });
})();
