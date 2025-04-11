// Global variables
let selectedRepo = null
let isWorkflowEnabled = false
const isLoading = false

// Initialize the page
document.addEventListener("DOMContentLoaded", () => {
  // Set default cron expression
  updateCronInputs("hourly")

  // Add event listeners to radio buttons
  document.querySelectorAll('input[name="schedule-type"]').forEach((radio) => {
    radio.addEventListener("change", function () {
      updateCronInputs(this.value)
    })
  })
})

// Show repository details
async function showRepoDetails(repoFullName, isPrivate) {
  // Set selected repo and update UI
  selectedRepo = repoFullName

  // Update active state in repo list
  document.querySelectorAll(".repo-card").forEach((card) => {
    card.classList.remove("active")
  })
  document.querySelector(`.repo-card[data-repo="${repoFullName}"]`).classList.add("active")

  // Update repo name in details panel
  document.getElementById("repo-name").textContent = repoFullName

  // Enable buttons
  document.getElementById("add-update-btn").disabled = false
  document.getElementById("delete-btn").disabled = false

  // Check if workflow is enabled for this repo
  await checkFeatureStatus(repoFullName)
}

// Check if workflow is enabled for a repository
async function checkFeatureStatus(repoFullName) {
  try {
    showLoading(true)

    const response = await fetch(`/check-feature-status?repository=${repoFullName}`)
    const data = await response.json()

    isWorkflowEnabled = data.enabled

    // Update UI based on status
    const statusElement = document.getElementById("feature-status")
    statusElement.textContent = isWorkflowEnabled ? "Enabled" : "Disabled"
    statusElement.className = `feature-status ${isWorkflowEnabled ? "enabled" : "disabled"}`

    // Update workflow badge in repo list
    const repoName = repoFullName.split("/")[1]
    const badgeElement = document.getElementById(`workflow-badge-${repoName}`)
    badgeElement.className = `workflow-badge ${isWorkflowEnabled ? "active" : "inactive"}`

    // Update add/update button text
    const addUpdateBtn = document.getElementById("add-update-btn")
    addUpdateBtn.innerHTML = isWorkflowEnabled
      ? '<i class="fas fa-sync button-icon"></i> Update Workflow'
      : '<i class="fas fa-plus button-icon"></i> Add Workflow'

    // Enable/disable delete button based on status
    document.getElementById("delete-btn").disabled = !isWorkflowEnabled

    showLoading(false)
  } catch (error) {
    console.error("Error checking feature status:", error)
    showNotification("Error checking workflow status", false)
    showLoading(false)
  }
}

// Add or update workflow
async function addOrUpdateWorkflow(repoFullName) {
  if (!repoFullName) return

  try {
    showLoading(true)

    const cronExpression = document.getElementById("cron-expression").textContent
    const response = await fetch("/add-workflow", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ repository: repoFullName, cron: cronExpression }),
    })

    const data = await response.json()

    showNotification(data.success ? "Workflow added/updated successfully!" : `Error: ${data.error}`, data.success)

    // Refresh status after adding/updating
    if (data.success) {
      await checkFeatureStatus(repoFullName)
    }

    showLoading(false)
  } catch (error) {
    console.error("Error:", error)
    showNotification("An unexpected error occurred", false)
    showLoading(false)
  }
}

// Delete workflow
async function deleteWorkflow(repoFullName) {
  if (!repoFullName) return

  try {
    showLoading(true)

    const response = await fetch("/delete-workflow", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ repository: repoFullName }),
    })

    const data = await response.json()

    showNotification(data.success ? "Workflow deleted successfully!" : `Error: ${data.error}`, data.success)

    // Refresh status after deleting
    if (data.success) {
      await checkFeatureStatus(repoFullName)
    }

    showLoading(false)
  } catch (error) {
    console.error("Error:", error)
    showNotification("An unexpected error occurred", false)
    showLoading(false)
  }
}

// Show notification
function showNotification(message, isSuccess) {
  const notification = document.getElementById("notification")
  const icon = isSuccess
    ? '<i class="fas fa-check-circle notification-icon"></i>'
    : '<i class="fas fa-exclamation-circle notification-icon"></i>'
  notification.innerHTML = icon + message
  notification.className = `notification ${isSuccess ? "success" : "error"}`

  // Hide notification after 3 seconds
  setTimeout(() => {
    notification.className = "notification hidden"
  }, 3000)
}

// Show/hide loading state
function showLoading(isLoading) {
  const addUpdateBtn = document.getElementById("add-update-btn")
  const deleteBtn = document.getElementById("delete-btn")

  if (isLoading) {
    addUpdateBtn.innerHTML = '<span class="spinner"></span> Processing...'
    deleteBtn.innerHTML = '<span class="spinner"></span> Processing...'
    addUpdateBtn.disabled = true
    deleteBtn.disabled = true
  } else {
    // Restore button text based on workflow status
    addUpdateBtn.innerHTML = isWorkflowEnabled
      ? '<i class="fas fa-sync button-icon"></i> Update Workflow'
      : '<i class="fas fa-plus button-icon"></i> Ad Workflow'
    deleteBtn.innerHTML = '<i class="fas fa-trash-alt button-icon"></i> Delete Workflow'

    // Enable buttons based on selection and status
    addUpdateBtn.disabled = !selectedRepo
    deleteBtn.disabled = !selectedRepo || !isWorkflowEnabled
  }
}

// Update cron inputs based on selected schedule type
function updateCronInputs(scheduleType) {
  const container = document.getElementById("schedule-config")
  container.innerHTML = ""

  switch (scheduleType) {
    case "hourly":
      container.innerHTML = `
                <div class="time-picker">
                    <label for="hour-interval">Run every</label>
                    <select id="hour-interval" onchange="generateCronExpression()">
                        <option value="1">1</option>
                        <option value="2">2</option>
                        <option value="3">3</option>
                        <option value="4">4</option>
                        <option value="6">6</option>
                        <option value="12">12</option>
                    </select>
                    <span>hour(s)</span>
                </div>
            `
      break

    case "daily":
      container.innerHTML = `
                <div class="time-picker">
                    <label for="daily-hour">Run at</label>
                    <select id="daily-hour" onchange="generateCronExpression()">
                        ${generateHourOptions()}
                    </select>
                    <span>every day</span>
                </div>
            `
      break

    case "weekly":
      container.innerHTML = `
                <div class="time-picker">
                    <label for="weekly-hour">Run at</label>
                    <select id="weekly-hour" onchange="generateCronExpression()">
                        ${generateHourOptions()}
                    </select>
                </div>
                <div class="day-picker">
                    <label>On these days:</label>
                    <div class="day-checkbox-group">
                        <label class="day-checkbox"><input type="checkbox" value="1" name="weekday" checked onchange="generateCronExpression()"> Monday</label>
                        <label class="day-checkbox"><input type="checkbox" value="2" name="weekday" onchange="generateCronExpression()"> Tuesday</label>
                        <label class="day-checkbox"><input type="checkbox" value="3" name="weekday" onchange="generateCronExpression()"> Wednesday</label>
                        <label class="day-checkbox"><input type="checkbox" value="4" name="weekday" onchange="generateCronExpression()"> Thursday</label>
                        <label class="day-checkbox"><input type="checkbox" value="5" name="weekday" onchange="generateCronExpression()"> Friday</label>
                        <label class="day-checkbox"><input type="checkbox" value="6" name="weekday" onchange="generateCronExpression()"> Saturday</label>
                        <label class="day-checkbox"><input type="checkbox" value="0" name="weekday" onchange="generateCronExpression()"> Sunday</label>
                    </div>
                </div>
            `
      break

    case "monthly":
      container.innerHTML = `
                <div class="time-picker">
                    <label for="monthly-hour">Run at</label>
                    <select id="monthly-hour" onchange="generateCronExpression()">
                        ${generateHourOptions()}
                    </select>
                </div>
                <div class="day-picker">
                    <label for="monthly-day">On day</label>
                    <select id="monthly-day" onchange="generateCronExpression()">
                        ${generateDayOptions()}
                    </select>
                    <span>of each month</span>
                </div>
            `
      break

    case "custom":
      container.innerHTML = `
                <div class="custom-cron">
                    <label for="custom-cron-input">Custom cron expression:</label>
                    <input type="text" id="custom-cron-input" placeholder="e.g., 0 */6 * * *" onchange="setCustomCronExpression()">
                    <p class="help-text">Format: minute hour day-of-month month day-of-week</p>
                </div>
            `
      break
  }

  // Generate initial cron expression
  generateCronExpression()
}

// Generate hour options for select elements
function generateHourOptions() {
  let options = ""
  for (let i = 0; i < 24; i++) {
    const hour = i.toString().padStart(2, "0")
    options += `<option value="${i}">${hour}:00</option>`
  }
  return options
}

// Generate day options for monthly schedule
function generateDayOptions() {
  let options = ""
  for (let i = 1; i <= 31; i++) {
    options += `<option value="${i}">${i}</option>`
  }
  return options
}

// Generate cron expression based on selected options
function generateCronExpression() {
  const scheduleType = document.querySelector('input[name="schedule-type"]:checked').value
  let cronExpression = "0 " // Default minute value is 0

  switch (scheduleType) {
    case "hourly":
      const hourInterval = document.getElementById("hour-interval").value
      cronExpression += `*/${hourInterval} * * *`
      break

    case "daily":
      const dailyHour = document.getElementById("daily-hour").value
      cronExpression += `${dailyHour} * * *`
      break

    case "weekly":
      const weeklyHour = document.getElementById("weekly-hour").value
      const selectedDays = Array.from(document.querySelectorAll('input[name="weekday"]:checked'))
        .map((checkbox) => checkbox.value)
        .join(",")
      cronExpression += `${weeklyHour} * * ${selectedDays || "*"}`
      break

    case "monthly":
      const monthlyHour = document.getElementById("monthly-hour").value
      const monthlyDay = document.getElementById("monthly-day").value
      cronExpression += `${monthlyHour} ${monthlyDay} * *`
      break

    case "custom":
      // Custom cron is handled separately
      return
  }

  document.getElementById("cron-expression").textContent = cronExpression
}

// Set custom cron expression
function setCustomCronExpression() {
  const customCron = document.getElementById("custom-cron-input").value
  if (customCron) {
    document.getElementById("cron-expression").textContent = customCron
  }
}

// Event listeners for buttons
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("add-update-btn").addEventListener("click", () => {
    addOrUpdateWorkflow(selectedRepo)
  })

  document.getElementById("delete-btn").addEventListener("click", () => {
    deleteWorkflow(selectedRepo)
  })
})
