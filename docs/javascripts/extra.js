function initLogoHomeRedirect() {
  function getHomeUrl() {
    // For this GitHub Pages project site, force the project base path.
    if (window.location.hostname.endsWith('github.io')) {
      return window.location.origin + '/pywatson/';
    }

    // Fallback for local/custom-domain previews.
    return window.location.origin + '/';
  }

  var homeUrl = getHomeUrl();
  var logoRoot = document.querySelector('.md-header__button.md-logo');
  if (!logoRoot) {
    return;
  }

  // Ensure native anchor navigation points to the correct site root.
  var logoAnchor = logoRoot.tagName === 'A' ? logoRoot : logoRoot.querySelector('a');
  if (logoAnchor) {
    logoAnchor.setAttribute('href', homeUrl);
  }

  // Defensive click handling for both container and anchor.
  var targets = [logoRoot, logoAnchor].filter(Boolean);
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
}

if (typeof document$ !== 'undefined' && document$.subscribe) {
  document$.subscribe(initLogoHomeRedirect);
} else {
  document.addEventListener('DOMContentLoaded', initLogoHomeRedirect);
}