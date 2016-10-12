var extractPages = function() {
  var resultStr = "";
  var elements = document.getElementsByClassName("desc-paragraph");
  for (var index in elements) {
    var element = elements[index];
    if (typeof(element) == 'object') {
      var pageName = element.childNodes[0].innerHTML;
      resultStr += "http://www." + pageName.toLowerCase() + "\n";
    }
  }
  console.log(resultStr.trim());
};
