// This javascript implements the logic for checking all 
// DOM elements with src or href attribute in the DOM tree
// and returns whether they appear in above the fold or not.

// isElementInViewPort takes a reference to a DOM element 
// and returns whether the element appears above-the-fold
// or not (in the viewport or not).
function isElementInViewport (el) {
    var rect = el.getBoundingClientRect();
    return (rect.top>-1 && rect.bottom <= screen.height);
}

// Get all elements in the DOM tree.
const all = document.getElementsByTagName("*");
for (var i = 0; i < all.length; i++) {
  var el = all[i];
  // Only care if the element has either href or src.
  if (!(el.hasAttribute("src") || el.hasAttribute("href"))) {
    continue
  }

  var isInViewport = isElementInViewport(el);
  var url = el.hasAttribute("src") ? el.src : el.href;
  console.log(url + " " + isInViewport);
}
