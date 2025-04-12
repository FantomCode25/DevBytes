function createReportButton(label) {
  const button = document.createElement("button");
  button.textContent = `Report as ${label}`;
  button.style.marginLeft = "10px";
  button.style.padding = "2px 6px";
  button.style.backgroundColor = label === "spam" ? "#ff4d4f" : "#4caf50";
  button.style.color = "white";
  button.style.border = "none";
  button.style.borderRadius = "4px";
  button.style.cursor = "pointer";
  button.className = "github-reporter-btn";
  button.onclick = async () => {
    // Find the comment text using different strategies based on comment type
    let commentText = "no comment";
    let parentElement = button.closest('.js-comment') || button.closest('.react-issue-comment');
    
    // For traditional GitHub comments
    const traditionalCommentBody = parentElement?.querySelector('.comment-body');
    // For React-based GitHub comments in issues
    const reactCommentBody = parentElement?.querySelector('[data-testid="markdown-body"]');
    
    if (traditionalCommentBody) {
      commentText = traditionalCommentBody.innerText.trim();
    } else if (reactCommentBody) {
      commentText = reactCommentBody.innerText.trim();
    }

    const username = document.querySelector('meta[name="user-login"]')?.content || "unknown-user";
    
    const response = await fetch("https://xgvwdzlifqqdorbkxgof.supabase.co/rest/v1/feedback", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "apikey": "",
        "Authorization": "Bearer "
      },
      body: JSON.stringify({
        github_username: username,
        comment: commentText,
        label: label
      })
    });
    
    if (response.ok) {
      alert(`Reported as ${label} successfully.`);
    } else {
      alert("Failed to report comment.");
    }
  };
  
  return button;
}

function injectButtons() {
  // Handle traditional GitHub comments
  document.querySelectorAll(".timeline-comment-actions:not(.buttons-added)").forEach(actionArea => {
    const spamBtn = createReportButton("spam");
    const hamBtn = createReportButton("ham");
    actionArea.appendChild(spamBtn);
    actionArea.appendChild(hamBtn);
    actionArea.classList.add("buttons-added");
  });
  
  // Handle React-based GitHub issue comments
  document.querySelectorAll('.react-issue-comment').forEach(commentContainer => {
    // Skip if we've already processed this comment
    if (commentContainer.classList.contains('buttons-added')) {
      return;
    }
    
    // Find the toolbar area - there are multiple possible locations for this
    // First try the comment header right side
    let targetContainer = commentContainer.querySelector('[data-testid="comment-header-right-side-items"] > div:first-child');
    
    // If that doesn't exist, try other common containers
    if (!targetContainer) {
      // The flex container next to the kebab menu
      targetContainer = commentContainer.querySelector('.Box-sc-g0xbh4-0.ezcJRX');
    }
    
    // If still not found, look for any toolbar-like container
    if (!targetContainer) {
      targetContainer = commentContainer.querySelector('[role="toolbar"]');
    }
    
    // Final fallback - just add to the comment header if we can find it
    if (!targetContainer) {
      targetContainer = commentContainer.querySelector('[data-testid="comment-header"]');
    }
    
    // If we found somewhere to put the buttons
    if (targetContainer) {
      // Check if buttons are already added
      if (!targetContainer.querySelector('.github-reporter-btn')) {
        // Create container for our buttons
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'report-buttons-container';
        buttonContainer.style.display = 'inline-flex';
        buttonContainer.style.gap = '4px';
        buttonContainer.style.marginLeft = '8px';
        
        const spamBtn = createReportButton("spam");
        const hamBtn = createReportButton("ham");
        
        buttonContainer.appendChild(spamBtn);
        buttonContainer.appendChild(hamBtn);
        
        // Safely append the buttons to the target container
        targetContainer.appendChild(buttonContainer);
      }
    }
    
    // Mark as processed
    commentContainer.classList.add('buttons-added');
  });
}

// Run initially and then check for new comments regularly
injectButtons();
setInterval(injectButtons, 2000); // Re-check every 2s for new comments

// Add a mutation observer to detect new comments being added
const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    if (mutation.addedNodes.length) {
      injectButtons();
      break;
    }
  }
});

// Start observing the document body for DOM changes
observer.observe(document.body, { 
  childList: true, 
  subtree: true 
});