const $ = id => document.getElementById(id);
let config, state = {jobs: [], library: []}, renderedJobs = '', renderedLibrary = '', failures = 0;
const statuses = {queued: 'Queued', extracting: 'Finding audio…', downloading: 'Downloading', converting: 'Creating MP3…', complete: 'Ready to listen', error: 'Needs attention'};
function element(tag, className, text) { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; }
function message(text, error = false) { $('form-message').textContent = text; $('form-message').className = error ? 'error' : ''; $('form-message').hidden = !text; }
async function request(path, options) { const response = await fetch(path, options); const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Something went wrong. Please try again.'); return data; }
async function createDownload(url, quality) {
  if (!config) return message('The studio is reconnecting. Please try again shortly.', true);
  $('submit').disabled = true;
  try { await request('/api/downloads', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-App-Token': config.token}, body: JSON.stringify({url, quality})}); message('Added to your studio. You can queue another video while this one downloads.'); $('url').value = ''; await refresh(); }
  catch (error) { message(error.message, true); }
  finally { $('submit').disabled = false; }
}
$('download-form').addEventListener('submit', event => { event.preventDefault(); createDownload($('url').value, $('quality').value); });
$('paste').addEventListener('click', async () => { try { $('url').value = await navigator.clipboard.readText(); $('url').focus(); } catch { message('Click the link field and paste with ⌘V or Ctrl+V.', true); $('url').focus(); } });
$('search').addEventListener('input', () => renderLibrary(true));
$('close-player').addEventListener('click', () => { $('audio').pause(); $('audio').removeAttribute('src'); $('audio').load(); $('player').hidden = true; document.querySelectorAll('.playing').forEach(n => n.classList.remove('playing')); });
function renderJobs() {
  const key = JSON.stringify(state.jobs); if (key === renderedJobs) return; renderedJobs = key;
  $('queue-section').hidden = !state.jobs.length;
  const active = state.jobs.filter(job => !['complete','error'].includes(job.status)).length;
  $('queue-count').textContent = active ? `${active} in progress` : 'All caught up';
  $('jobs').replaceChildren();
  for (const job of state.jobs) {
    const card = element('div', `job ${job.status}`), top = element('div', 'job-top');
    top.append(element('span', 'job-title', job.title), element('span', 'job-status', statuses[job.status] + (job.status === 'downloading' ? ` · ${job.progress}%` : ''))); card.append(top);
    if (!['complete','error'].includes(job.status)) { const bar = element('div', 'progress'), fill = element('span'); fill.style.width = `${job.progress || 3}%`; bar.setAttribute('role','progressbar'); bar.setAttribute('aria-label','Download progress'); bar.setAttribute('aria-valuenow',job.progress); bar.setAttribute('aria-valuemin','0'); bar.setAttribute('aria-valuemax','100'); bar.append(fill); card.append(bar); }
    if (job.error) { card.append(element('p','job-error',job.error)); const retry = element('button','retry','Try again'); retry.type = 'button'; retry.addEventListener('click', () => createDownload(job.url, job.quality)); card.append(retry); }
    $('jobs').append(card);
  }
}
function renderLibrary(force = false) {
  const key = JSON.stringify(state.library); if (!force && key === renderedLibrary) return; renderedLibrary = key;
  $('library-count').textContent = $('nav-count').textContent = state.library.length;
  const query = $('search').value.toLocaleLowerCase();
  const files = state.library.filter(file => file.title.toLocaleLowerCase().includes(query)); $('library-list').replaceChildren();
  if (!files.length) { const empty = element('div','empty'); empty.append(element('div','empty-icon','♫'), element('strong','',query ? 'No matching audio' : 'Your collection starts here'), element('p','',query ? 'Try another title or clear your search.' : 'Paste a video link above. Your finished MP3s will appear here, ready to play.')); $('library-list').append(empty); return; }
  for (const file of files) {
    const row = element('article','track'), cover = element('div','cover','♫'), info = element('div','track-info'), actions = element('div','track-actions');
    const title = file.title.replace(/ \[[\w-]{11}\]$/, '');
    info.append(element('strong','',title), element('small','',`MP3 · ${(file.bytes / 1048576).toFixed(1)} MB · ${new Date(file.modified * 1000).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'})}`));
    const play = element('button','play-button','▶'); play.type = 'button'; play.setAttribute('aria-label',`Play ${title}`);
    play.addEventListener('click', async () => { document.querySelectorAll('.playing').forEach(n => n.classList.remove('playing')); row.classList.add('playing'); $('playing-title').textContent = title; $('player').hidden = false; $('audio').src = `/audio/${file.id}`; try { await $('audio').play(); } catch { message('Use the player controls to start playback.', true); } });
    const save = element('a','save-link','Save MP3 ↓'); save.href = `/audio/${file.id}?download=1`; save.setAttribute('aria-label',`Save ${title}`);
    actions.append(play,save); row.append(cover,info,actions); $('library-list').append(row);
  }
}
async function refresh() {
  try { if (!config) { config = await request('/api/config'); const deps = config.dependencies; $('setup').textContent = `Library: ${config.directory}. yt-dlp ${deps.yt_dlp}. FFmpeg ${deps.ffmpeg ? 'ready' : 'missing'}. JavaScript runtime ${deps.javascript ? 'ready' : 'missing'}.`; if (!deps.ffmpeg || !deps.javascript) message('Install the missing dependencies listed in Studio setup, then restart the app.', true); }
    state = await request('/api/state'); renderJobs(); renderLibrary(); if (failures) message('Connected to your studio again.'); failures = 0;
  } catch { failures++; config = null; message('Connection lost. Keep the local server running; we’ll reconnect automatically.', true); }
}
async function poll() { await refresh(); setTimeout(poll, 1500); }
poll();
