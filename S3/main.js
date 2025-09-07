document.addEventListener('DOMContentLoaded', function() {
    const emailPlaceholder = document.getElementById('emailPlaceholder');
    if(emailPlaceholder) {
        emailPlaceholder.addEventListener('click', function() {
            const email = 'your.name' + '@' + 'example.com';
            this.innerHTML = `<a href="mailto:${email}" style="color:#ecf0f1;text-decoration:none">${email}</a>`;
            this.style.cursor = 'auto';
        });
    }
});