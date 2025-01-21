// ZEE
document.getElementById("scrape-button").addEventListener("click", () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.tabs.sendMessage(tabs[0].id, { action: "scrape" }, (response) => {
        if (response && response.data) {
          // Convert data to CSV
          const csv = convertToCSV(response.data);
  
          // Create a Blob and trigger the download
          const blob = new Blob([csv], { type: "text/csv" });
          const url = URL.createObjectURL(blob);
  
          // Create a temporary link to trigger the download
          const a = document.createElement("a");
          a.href = url;
          a.download = "menu_items.csv";
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
  
          alert("Data scraped and downloaded successfully!");
        } else {
          alert("Failed to scrape data.");
        }
      });
    });
  });
  
  // Helper function to convert JSON to CSV
  function convertToCSV(data) {
    const headers = ["Title", "Description", "Price", "Image"];
    const rows = data.map((item) => {
      return [
        `"${item.title || ""}"`,
        `"${item.description || ""}"`,
        `"${item.price || ""}"`,
        `"${item.image || ""}"`,
      ].join(",");
    });
  
    return [headers.join(","), ...rows].join("\n");
  }