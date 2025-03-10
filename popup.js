document.getElementById("scrape-button").addEventListener("click", () => scrapeData("full"));
document.getElementById("scrape-export-no-ai").addEventListener("click", () => scrapeData("no-ai"));
document.getElementById("scrape-products-only").addEventListener("click", () => scrapeData("products-only"));

function scrapeData(mode) {
    const loadingContainer = document.getElementById("loading-container");
    loadingContainer.style.display = "block"; // Show loader

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        chrome.tabs.sendMessage(tabs[0].id, { action: "scrape" }, (response) => {
            if (response && response.data.length > 0) {
                sendDataToFlask(mode, response.sheetName, response.data);
            } else {
                alert("Failed to scrape data.");
                loadingContainer.style.display = "none"; // Hide loader on failure
            }
        });
    });
}

async function sendDataToFlask(mode, sheetName, data) {
    const flaskUrl = "http://128.140.37.194:5001/create-sheet"; // Flask server URL

    // Modify data based on selected mode
    if (mode === "products-only") {
        data = data.map(item => ({ title: item.title }));
    }

    try {
        const response = await fetch(flaskUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: mode, sheet_name: sheetName, values: data })
        });

        const result = await response.json();
        if (result.status === "success" && result.sheetUrl) {
            chrome.tabs.create({ url: result.sheetUrl }); // Open the new Google Sheet
        } else {
            alert("Error: " + result.message);
        }
    } catch (error) {
        alert("Failed to send data to Flask. Is the server running?");
    } finally {
        document.getElementById("loading-container").style.display = "none"; // Hide loader
    }
}
