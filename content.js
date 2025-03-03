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

      // Get Sheet Name from XPath
      let sheetName = "";
      try {
          let sheetTitleElement = document.evaluate(
              '//*[@id="__next"]/main/header/div/div[2]/div[1]/div[1]/h1',
              document,
              null,
              XPathResult.FIRST_ORDERED_NODE_TYPE,
              null
          ).singleNodeValue;

          if (sheetTitleElement) {
              sheetName = sheetTitleElement.innerText.trim();
          }
      } catch (error) {
          console.error("Error extracting sheet name:", error);
      }

      sendResponse({ sheetName: sheetName || "Default Sheet", data: menuItems });
  }
});
