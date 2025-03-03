document.getElementById("scrape-button").addEventListener("click", () => {
  const scrapeButton = document.getElementById("scrape-button");
  const loadingContainer = document.getElementById("loading-container");

  // Disable button and show loading animation
  scrapeButton.disabled = true;
  scrapeButton.innerText = "Scraping...";
  loadingContainer.style.display = "block";

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.tabs.sendMessage(tabs[0].id, { action: "scrape" }, (response) => {
          if (response && response.data.length > 0) {
              sendDataToFlask(response.sheetName, response.data);
          } else {
              alert("Failed to scrape data.");
              resetUI();
          }
      });
  });
});

async function sendDataToFlask(sheetName, data) {
  const flaskUrl = "http://127.0.0.1:5000/create-sheet"; // Flask server URL

  try {
      const response = await fetch(flaskUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sheet_name: sheetName, values: data })
      });

      const result = await response.json();
      console.log("Flask Response:", result);

      if (result.status === "success" && result.sheetUrl) {
          chrome.tabs.create({ url: result.sheetUrl }); // Open the new Google Sheet
      } else {
          alert("Error: " + result.message);
      }
  } catch (error) {
      console.error("Error:", error);
      alert("Failed to send data to Flask. Is the server running?");
  } finally {
      resetUI(); // Reset UI after request is complete
  }
}

function resetUI() {
  const scrapeButton = document.getElementById("scrape-button");
  const loadingContainer = document.getElementById("loading-container");

  scrapeButton.disabled = false;
  scrapeButton.innerText = "Scrape Menu";
  loadingContainer.style.display = "none";
}
