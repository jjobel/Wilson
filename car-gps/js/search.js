/* search.js — Nominatim geocoding & search UI */

const Search = (() => {
  const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search';
  let debounceTimer = null;
  let onSelect = null;

  function init(onDestinationSelected) {
    onSelect = onDestinationSelected;

    const input = document.getElementById('search-input');
    const clearBtn = document.getElementById('search-clear');
    const resultsList = document.getElementById('search-results');

    input.addEventListener('input', () => {
      const q = input.value.trim();
      clearBtn.style.display = q ? 'block' : 'none';

      clearTimeout(debounceTimer);
      if (q.length < 3) {
        resultsList.innerHTML = '';
        return;
      }
      debounceTimer = setTimeout(() => geocode(q), 400);
    });

    clearBtn.addEventListener('click', () => {
      input.value = '';
      clearBtn.style.display = 'none';
      resultsList.innerHTML = '';
      input.focus();
    });

    // Close results on outside tap
    document.addEventListener('click', (e) => {
      if (!e.target.closest('#search-panel')) {
        resultsList.innerHTML = '';
      }
    });
  }

  async function geocode(query) {
    const resultsList = document.getElementById('search-results');
    try {
      const params = new URLSearchParams({
        q: query,
        format: 'json',
        limit: '5',
        addressdetails: '1',
      });

      const resp = await fetch(`${NOMINATIM_URL}?${params}`, {
        headers: { 'Accept': 'application/json' },
      });

      if (!resp.ok) return;
      const data = await resp.json();

      resultsList.innerHTML = '';
      data.forEach((item) => {
        const li = document.createElement('li');
        li.textContent = item.display_name;
        li.addEventListener('click', () => {
          resultsList.innerHTML = '';
          document.getElementById('search-input').value = item.display_name.split(',')[0];
          if (onSelect) {
            onSelect({
              lat: parseFloat(item.lat),
              lng: parseFloat(item.lon),
              name: item.display_name,
            });
          }
        });
        resultsList.appendChild(li);
      });
    } catch (err) {
      console.error('Geocode error:', err);
    }
  }

  function clearSearch() {
    document.getElementById('search-input').value = '';
    document.getElementById('search-clear').style.display = 'none';
    document.getElementById('search-results').innerHTML = '';
  }

  function hide() {
    document.getElementById('search-panel').style.display = 'none';
  }

  function show() {
    document.getElementById('search-panel').style.display = '';
  }

  return { init, clearSearch, hide, show };
})();
