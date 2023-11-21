document.addEventListener('DOMContentLoaded', (event) => {
  const typeDropdown = document.querySelector('#type');
  const plDropdownParent = document.querySelector('#cs-pl-parent');
  const plDropdown = document.querySelector('#cs-pl');
  const etypeDropdown = document.querySelector('#etype');
  const eplDropdownParent = document.querySelector('#ecs-pl-parent');
  const eplDropdown = document.querySelector('#ecs-pl');

  hljs.listLanguages().forEach((language) => {
    const newElement = document.createElement('option');
    const enewElement = document.createElement('option');
    newElement.setAttribute('value', language)
    newElement.innerText = language;
    enewElement.setAttribute('value', language)
    enewElement.innerText = language;
    plDropdown.appendChild(newElement);
    eplDropdown.appendChild(enewElement);
  });

  if(plDropdown.value === '1') {
    plDropdownParent.style.display = 'block';
  } else if (plDropdown.value === '0') {
    plDropdownParent.style.display = 'none';
  }


  typeDropdown.addEventListener('change', (e) => {
    const newValue = e.target.value;
    if(newValue === '1') {
      plDropdownParent.style.display = 'block';
    } else if (newValue === '0') {
      plDropdownParent.style.display = 'none';
    }
  });

  if(eplDropdown.value === '1') {
    eplDropdownParent.style.display = 'block';
  } else if (eplDropdown.value === '0') {
    eplDropdownParent.style.display = 'none';
  }


  etypeDropdown.addEventListener('change', (e) => {
    const newValue = e.target.value;
    if(newValue === '1') {
      eplDropdownParent.style.display = 'block';
    } else if (newValue === '0') {
      eplDropdownParent.style.display = 'none';
    }
  });
});
