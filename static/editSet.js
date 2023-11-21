document.addEventListener('DOMContentLoaded', (event) => {
  const btns = Array.from(document.querySelectorAll('button.editBtn'));
  const names = Array.from(document.querySelectorAll('h4'));
  const inputField = document.querySelector('input[type="hidden"]');
  console.log(btns);
  let idx = 0;
  btns.forEach((btn) => {
    btn.setAttribute('data-btn-idx', idx);
    idx++;
    btn.addEventListener('click', (e) => {
      inputField.setAttribute('value', names[btn.getAttribute('data-btn-idx')]);
    });
  });
});
