document$.subscribe(function() {
  // Get the site URL from the base tag or use current origin
  var base = document.querySelector('base');
  var homeUrl = base ? base.href : window.location.origin + '/';

  // Make logo clickable (if not already wrapped in a link)
  var logo = document.querySelector('.md-header__button.md-logo');
  if (logo && !logo.classList.contains('clickable-added')) {
    logo.style.cursor = 'pointer';
    logo.addEventListener('click', function(e) {
      if (e.target.tagName !== 'A') {
        window.location.href = homeUrl;
      }
    });
    logo.classList.add('clickable-added');
  }

  // Make header title clickable to navigate to home page
  var headerTitle = document.querySelector('.md-header__title');
  if (headerTitle && !headerTitle.classList.contains('clickable-added')) {
    headerTitle.style.cursor = 'pointer';
    headerTitle.addEventListener('click', function(e) {
      if (e.target.tagName !== 'A') {
        window.location.href = homeUrl;
      }
    });
    headerTitle.classList.add('clickable-added');
  }
});