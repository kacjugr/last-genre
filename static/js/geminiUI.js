// UI layer for Gemini recommendations: fetch progress, the reply text, and the
// paged artist modal. Kept separate from gemini.js (which only talks to the
// network) so a future <genAI>UI.js could reuse the same shape — createXUI(els)
// returning { fetchAndDisplay(genre, artists) } — for a different provider.
import { splitGeminiReply, fetchGeminiRecommendation } from "./gemini.js";
import { fetchArtwork } from "./spotify.js";

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// The prompt asks Gemini for 'albums'/'tracks', but tolerate the 'recommended_*'
// names it's used before, in case a reply still comes back that way.
function normalizeAlbums(artist) {
  if (Array.isArray(artist.albums)) return artist.albums;
  if (Array.isArray(artist.recommended_albums)) return artist.recommended_albums;
  if (artist.album && typeof artist.album === 'object') return [artist.album];
  return [];
}

function getAlbumTracks(album) {
  if (Array.isArray(album.tracks)) return album.tracks;
  if (Array.isArray(album.recommended_tracks)) return album.recommended_tracks;
  return [];
}

// els: { geminiBtn, statusEl, replyEl, geminiViewBtn, modalRoot }
// modalRoot is the modal's outer overlay element; the pieces inside it are found by
// the classes already on the markup (see templates/index.html's modal-overlay block).
// Returns { fetchAndDisplay(genre, artists) }. All state (recommendations, artwork,
// modal page) lives in this closure, private to this instance.
export function createGeminiUI(els) {
  var modal = {
    overlay: els.modalRoot,
    content: els.modalRoot.querySelector('.modal-content'),
    prev: els.modalRoot.querySelector('.modal-arrow-left'),
    next: els.modalRoot.querySelector('.modal-arrow-right'),
    pageIndicator: els.modalRoot.querySelector('.modal-page-indicator'),
    close: els.modalRoot.querySelector('.modal-close'),
  };
  var currentRecommendations = null;
  var currentText = null;
  var currentArtwork = null;
  var modalPage = 0;

  // artist page: a header row (Spotify artist image + bolded name), then a table of
  // recommended albums — album art, album title, recommended track names.
  function renderArtistPage(artist, artwork) {
    var html = '<div class="modal-artist-header">';
    if (artwork && artwork.image) {
      html += '<img class="modal-artist-thumb" src="' + esc(artwork.image) + '" alt="">';
    }
    html += '<h3 class="modal-artist-name">' + esc(artist.name || '') + '</h3></div>';

    if (artist.description) html += '<p>' + esc(artist.description) + '</p>';
    if (artist.fit) html += '<p><em>' + esc(artist.fit) + '</em></p>';

    var albums = normalizeAlbums(artist);
    var artworkAlbums = (artwork && Array.isArray(artwork.albums)) ? artwork.albums : [];
    if (albums.length) {
      html += '<table class="modal-album-table"><tbody>';
      albums.forEach(function (album, i) {
        var albumImage = artworkAlbums[i] && artworkAlbums[i].image;
        var tracks = getAlbumTracks(album);
        html += '<tr>' +
          '<td class="modal-album-art">' + (albumImage ? '<img src="' + esc(albumImage) + '" alt="">' : '') + '</td>' +
          '<td class="modal-album-title"><h4>' + esc(album.title || '') + '</h4></td>' +
          '<td class="modal-album-tracks">' +
            (tracks.length
              ? '<ul>' + tracks.map(function (t) { return '<li>' + esc((t && t.title) || '') + '</li>'; }).join('') + '</ul>'
              : '') +
          '</td></tr>';
      });
      html += '</tbody></table>';
    }
    return html;
  }

  // page 0 is the prose intro, pages 1..n are artist entries
  function renderModalPage() {
    var artists = Array.isArray(currentRecommendations) ? currentRecommendations : [];
    var pageCount = 1 + artists.length;

    if (modalPage === 0) {
      modal.content.innerHTML = '<p>' + esc(currentText || '').replace(/\n+/g, '</p><p>') + '</p>';
    } else {
      var artist = artists[modalPage - 1];
      var artwork = currentArtwork && currentArtwork[modalPage - 1];
      modal.content.innerHTML = renderArtistPage(artist, artwork);
    }

    modal.prev.disabled = modalPage === 0;
    modal.next.disabled = modalPage === pageCount - 1;
    modal.pageIndicator.textContent = (modalPage + 1) + ' / ' + pageCount;
  }

  function openModal() {
    modalPage = 0;
    renderModalPage();
    modal.overlay.style.display = 'flex';
  }

  function closeModal() {
    modal.overlay.style.display = 'none';
  }

  modal.prev.addEventListener('click', function () {
    if (modalPage > 0) { modalPage -= 1; renderModalPage(); }
  });
  modal.next.addEventListener('click', function () {
    var artists = Array.isArray(currentRecommendations) ? currentRecommendations : [];
    if (modalPage < artists.length) { modalPage += 1; renderModalPage(); }
  });
  modal.close.addEventListener('click', closeModal);
  modal.overlay.addEventListener('click', function (e) {
    if (e.target === modal.overlay) closeModal();
  });
  document.addEventListener('keydown', function (e) {
    if (modal.overlay.style.display === 'none') return;
    if (e.key === 'Escape') closeModal();
    if (e.key === 'ArrowLeft') modal.prev.click();
    if (e.key === 'ArrowRight') modal.next.click();
  });
  els.geminiViewBtn.addEventListener('click', openModal);

  function handleEvent(ev) {
    switch (ev.type) {
      case 'trying':
        els.statusEl.textContent = 'Asking Gemini… (attempt ' + ev.attempt + ')';
        break;
      case 'waiting':
        els.statusEl.textContent = 'Gemini busy — retrying in ' + ev.remaining + 's…';
        break;
      case 'trying_fallback':
        els.statusEl.textContent = 'Trying backup model…';
        break;
      case 'done':
        els.geminiBtn.disabled = false;
        if (ev.fallback) {
          els.statusEl.textContent =
            "Gemini's main model was busy after " + ev.retries +
            (ev.retries === 1 ? ' retry' : ' retries') +
            ', so the backup model answered instead:';
        } else if (ev.retries > 0) {
          els.statusEl.textContent =
            'Gemini was busy, but responded after ' + ev.retries +
            (ev.retries === 1 ? ' retry' : ' retries') + ':';
        } else {
          els.statusEl.style.display = 'none';
        }
        var parts = splitGeminiReply(ev.reply);
        currentRecommendations = parts.json;
        currentText = parts.text;
        console.log('Gemini JSON portion:', currentRecommendations);
        els.replyEl.textContent = parts.text;
        els.replyEl.style.display = 'block';
        currentArtwork = null;
        els.geminiViewBtn.style.display =
          (Array.isArray(currentRecommendations) && currentRecommendations.length) ? 'inline-block' : 'none';
        if (Array.isArray(currentRecommendations) && currentRecommendations.length) {
          fetchArtwork(currentRecommendations)
            .then(function (artworkData) {
              currentArtwork = artworkData.artwork || null;
              renderModalPage(); // no-op if the modal isn't showing an artist page yet
            })
            .catch(function () { /* artwork is enrichment, not critical — leave images blank */ });
        }
        break;
      case 'busy':
        els.geminiBtn.disabled = false;
        els.statusEl.textContent = 'Gemini is busy right now. Please try again in a bit.';
        break;
      case 'error':
        els.geminiBtn.disabled = false;
        els.statusEl.textContent = 'Error: ' + ev.message;
        break;
    }
  }

  function fetchAndDisplay(genre, artists) {
    els.geminiBtn.disabled = true;
    els.statusEl.textContent = 'Asking Gemini…';
    els.statusEl.style.display = 'block';
    els.replyEl.style.display = 'none';
    els.replyEl.textContent = '';
    els.geminiViewBtn.style.display = 'none';

    return fetchGeminiRecommendation(genre, artists, handleEvent)
      .catch(function (err) {
        els.geminiBtn.disabled = false;
        els.statusEl.textContent = 'Error contacting Gemini: ' + err;
      });
  }

  return { fetchAndDisplay: fetchAndDisplay };
}
