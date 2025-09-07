document.addEventListener('DOMContentLoaded', () => {
  const counterSpan = document.getElementById('counter');
  //Change it :   const apiUrl = 'https://your-api-id.execute-api.region.amazonaws.com/PROD/counter';
  const apiUrl = 'https://your-api-id.execute-api.region.amazonaws.com/PROD/counter';
  
  // Get visitor count
  function guncelleZiyaretciSayisi() {
    fetch(apiUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      counterSpan.textContent = data.count || 0;
    })
    .catch(error => {
      console.error('Ziyaretçi sayısı alınırken hata oluştu:', error);
      counterSpan.textContent = 'Error loading count';
    });
  }
  
  // Register new visitor  
  function kaydetZiyaretci() {
    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({})
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      console.log('Ziyaretçi sayısı başarıyla güncellendi:', data);
      if (data.count) {
        counterSpan.textContent = data.count;
      } else {
        guncelleZiyaretciSayisi();
      }
    })
    .catch(error => {
      console.error('Yeni ziyaretçi kaydedilirken hata oluştu:', error);
    });
  }
  
  guncelleZiyaretciSayisi();
  setTimeout(kaydetZiyaretci, 500);
});