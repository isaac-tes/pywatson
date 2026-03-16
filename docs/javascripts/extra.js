document$.subscribe(function () {
  function getHomeUrl() {
    // On GitHub project pages, keep the first path segment (repo name), e.g. /pywatson/.
    var parts = window.location.pathname.split('/').filter(Boolean);
    var firstSegment = parts.length > 0 ? parts[0] : '';
    if (window.location.hostname.endsWith('github.io') && firstSegment) {
      return window.location.origin + '/' + firstSegment + '/';
    }

    // Fallback for custom domains / local previews.
    return window.location.origin + '/';
  }

  var homeUrl = getHomeUrl();

  // Make both the logo container and inner anchor consistently navigate to homeUrl.
  var targets = document.querySelectorAll('.md-header__button.md-logo, .md-header__button.md-logo a');
  targets.forEach(function (target) {
    if (target.classList.contains('clickable-added')) {
      return;
    }
    target.style.cursor = 'pointer';
    target.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      window.location.href = homeUrl;
    });
    target.classList.add('clickable-added');
  });
});