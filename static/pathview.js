function getCookie(cname) {
  let name = cname + "=";
  let decodedCookie = decodeURIComponent(document.cookie);
  let ca = decodedCookie.split(';');
  for(let i = 0; i <ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) == ' ') {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
      return c.substring(name.length, c.length);
    }
  }
  return "";
}


document.addEventListener('DOMContentLoaded', function(event) {
  const setPath = getCookie('current_set');
  const tagPath = getCookie('current_tag_name');
  const backBtn = document.querySelector('#btn-back')
  let prev_path = 'javacript:void(0)';
  if (setPath !== '') {
    const path1 = document.querySelector('#set-path');
    path1.innerText = setPath.replace('.db', '');
    prev_path = '/sets';
  }
  if (tagPath !== '') {
    const path2 = document.querySelector('#tag-path');
    const pathSep = document.querySelector('#slash-path-sep');
    path2.innerText = tagPath;
    pathSep.innerText = '/';
    prev_path = `/sets/${setPath.replace('.db', '')}`
  }
  backBtn.href = prev_path;
});
