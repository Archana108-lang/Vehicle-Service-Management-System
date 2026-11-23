// Floating labels
document.querySelectorAll('.form-control').forEach(input => {
    if (input.value) {
        input.parentNode.querySelector('.floating-label').classList.add('active');
    }
    input.addEventListener('focus', () => {
        input.parentNode.querySelector('.floating-label').classList.add('active');
    });
    input.addEventListener('blur', () => {
        if (!input.value) {
            input.parentNode.querySelector('.floating-label').classList.remove('active');
        }
    });
});

// Star creation
function createStars() {
    const starsContainer = document.getElementById('night-sky');
    for (let i = 0; i < 150; i++) {
        const star = document.createElement('div');
        star.classList.add('star');
        star.style.width = Math.random() * 3 + 'px';
        star.style.height = star.style.width;
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.animationDelay = Math.random() * 5 + 's';
        star.style.opacity = Math.random() * 0.7 + 0.3;
        starsContainer.appendChild(star);
    }
}
createStars();
