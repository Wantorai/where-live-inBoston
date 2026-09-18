const statusMessage = document.querySelector("#connection-status");
const checkButton = document.querySelector("#check-connection");

async function checkConnection() {
  checkButton.disabled = true;
  statusMessage.dataset.state = "loading";
  statusMessage.textContent = "Checking connection…";

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000);

  try {
    const response = await fetch("/api/health", {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error("The API returned an unsuccessful response.");
    }

    const data = await response.json();
    if (data?.status !== "ok") {
      throw new Error("The API returned an unexpected status.");
    }

    statusMessage.dataset.state = "success";
    statusMessage.textContent = "Connected. The application is responding.";
  } catch {
    statusMessage.dataset.state = "error";
    statusMessage.textContent = "Unable to confirm the connection. Please try again.";
  } finally {
    clearTimeout(timeoutId);
    checkButton.disabled = false;
  }
}

checkButton.addEventListener("click", checkConnection);
checkConnection();
