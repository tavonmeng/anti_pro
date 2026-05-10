const revealEls = document.querySelectorAll(".reveal");

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.18 }
);

revealEls.forEach((el) => observer.observe(el));

document.querySelector("form")?.addEventListener("submit", (event) => {
  event.preventDefault();
});

const caseSection = document.querySelector(".case-section");
const caseStories = [...document.querySelectorAll(".case-story")];
const casePages = [...document.querySelectorAll(".case-page")];
const caseProgress = document.querySelector(".case-progress-fill");

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
const contentSwapAngle = 84;

function updateCaseFlipbook() {
  if (!caseSection || casePages.length === 0) return;

  const sectionTop = caseSection.offsetTop;
  const scrollable = caseSection.offsetHeight - window.innerHeight;
  const progress = scrollable > 0
    ? clamp((window.scrollY - sectionTop) / scrollable, 0, 1)
    : 0;
  const pageCount = casePages.length;
  const segmentCount = pageCount - 1;
  const rawStep = progress * segmentCount;
  const currentTurn = Math.min(Math.floor(rawStep), segmentCount - 1);
  const segmentProgress = segmentCount > 0 ? rawStep - currentTurn : 0;
  const flipWindow = 0.78;
  const localProgress = clamp(segmentProgress / flipWindow, 0, 1);
  const currentEased = 1 - Math.pow(1 - localProgress, 2.4);
  const hasCrossedCenter = currentEased * 180 >= contentSwapAngle;
  const activeIndex = progress >= 0.995
    ? pageCount - 1
    : Math.min(currentTurn + (hasCrossedCenter ? 1 : 0), pageCount - 1);

  caseStories.forEach((story, index) => {
    story.classList.toggle("is-active", index === activeIndex);
  });

  casePages.forEach((page, index) => {
    let turn = 0;
    if (index < currentTurn) turn = 1;
    if (index === currentTurn) turn = localProgress;
    if (progress >= 0.995 && index < pageCount - 1) turn = 1;

    const eased = 1 - Math.pow(1 - clamp(turn, 0, 1), 2.4);
    const angle = -180 * eased;
    const hasCrossedCenter = Math.abs(angle) >= contentSwapAngle;
    page.style.transform = `rotateY(${angle}deg)`;
    page.style.zIndex = String(pageCount - index + (index === currentTurn ? 20 : 0));
    page.style.visibility = "visible";
    page.classList.toggle("is-back", hasCrossedCenter);
    page.classList.toggle("is-turned", turn >= 1);
    page.style.setProperty("--page-shadow", String(Math.sin(clamp(turn, 0, 1) * Math.PI)));
  });

  if (caseProgress) {
    caseProgress.style.transform = `scaleX(${progress})`;
  }
}

let ticking = false;
function requestCaseFlipbookUpdate() {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    updateCaseFlipbook();
    ticking = false;
  });
}

window.addEventListener("scroll", requestCaseFlipbookUpdate, { passive: true });
window.addEventListener("resize", requestCaseFlipbookUpdate);
updateCaseFlipbook();
