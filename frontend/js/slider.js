// frontend/js/slider.js

document.addEventListener("DOMContentLoaded", () => {
    console.log("Slider script loaded."); // 1. Verify script runs
  
    const sliderImagesContainer = document.querySelector(".slider-images");
    const images = sliderImagesContainer.querySelectorAll("img");
    const prevBtn = document.getElementById("prev-btn");
    const nextBtn = document.getElementById("next-btn");
    const zoomModal = document.getElementById("zoom-modal");
    const zoomedImage = document.getElementById("zoomed-image");
    const closeModalBtn = document.querySelector(".close-modal");
  
    // 2. Verify elements are found
    console.log("Slider container:", sliderImagesContainer);
    console.log("Modal:", zoomModal);
    console.log("Zoomed image element:", zoomedImage);
    if (!sliderImagesContainer || !zoomModal || !zoomedImage) {
      console.error("ERROR: Could not find essential slider/modal elements!");
      return; // Stop if elements are missing
    }
  
    let currentIndex = 0;
    const totalImages = images.length;
  
    function updateSlider() {
      // console.log("Updating slider, current index:", currentIndex); // Optional: uncomment for more detail
      images.forEach((img, index) => {
        img.classList.remove("active", "previous");
        img.style.cursor = "default";
  
        if (index === currentIndex) {
          img.classList.add("active");
          img.style.cursor = "zoom-in";
        } else if (index < currentIndex) {
          img.classList.add("previous");
        }
      });
  
      prevBtn.disabled = currentIndex === 0;
      nextBtn.disabled = currentIndex === totalImages - 1;
    }
  
    function openZoomModal(imageSrc) {
      console.log("Attempting to open zoom modal with src:", imageSrc); // 5. Check if this function is called
      if (!zoomedImage || !zoomModal) {
        console.error("Cannot open modal, elements missing.");
        return;
      }
      zoomedImage.src = imageSrc;
      zoomModal.classList.add("visible");
      console.log("Added 'visible' class to modal:", zoomModal.classList); // 6. Verify class is added
      document.body.style.overflow = "hidden";
    }
  
    function closeZoomModal() {
      // console.log("Closing zoom modal."); // Optional
      if (!zoomModal) return;
      zoomModal.classList.remove("visible");
      zoomedImage.src = "";
      document.body.style.overflow = "";
    }
  
    // --- Event Listeners ---
  
    nextBtn.addEventListener("click", () => {
      if (currentIndex < totalImages - 1) {
        currentIndex++;
        updateSlider();
      }
    });
  
    prevBtn.addEventListener("click", () => {
      if (currentIndex > 0) {
        currentIndex--;
        updateSlider();
      }
    });
  
    // --- Zoom Functionality Listeners ---
  
    sliderImagesContainer.addEventListener("click", (event) => {
      console.log("Click detected inside slider container."); // 3. Check if click is registered
      console.log("Clicked element (event.target):", event.target); // What exactly was clicked?
  
      // Check if the clicked element is an IMG tag AND has the 'active' class
      const isImage = event.target.tagName === "IMG";
      const isActive = event.target.classList.contains("active");
      console.log(`Is image? ${isImage}, Is active? ${isActive}`); // 4. Check conditions
  
      if (isImage && isActive) {
        console.log("Conditions met! Calling openZoomModal...");
        openZoomModal(event.target.src);
      } else {
        console.log("Conditions not met for zoom.");
      }
    });
  
    zoomModal.addEventListener("click", (event) => {
      if (event.target === zoomModal) {
        closeZoomModal();
      }
    });
  
    closeModalBtn.addEventListener("click", closeZoomModal);
  
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && zoomModal.classList.contains("visible")) {
        closeZoomModal();
      }
    });
  
    // --- Initial Setup ---
    updateSlider();
    console.log("Initial slider update complete."); // 7. Verify initial setup runs
  });
  