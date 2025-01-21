chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "scrape") {
      const menuItems = [];
      const items = document.querySelectorAll("button.card.p-6.menu-item");
  
      items.forEach((item) => {
        const title = item.querySelector("h2.menu-item-title")?.innerText.trim();
        const description = item.querySelector("p.menu-item-description")?.innerText.trim();
        const price = item.querySelector("p.text-greenBadge")?.innerText.trim();
        const image = item.querySelector("img")?.src;
  
        menuItems.push({ title, description, price, image });
      });
  
      // Send the scraped data to the popup script
      sendResponse({ data: menuItems });
    }
  });