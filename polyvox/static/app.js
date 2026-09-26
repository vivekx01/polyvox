(function () {
  const form = document.getElementById("generate-form");
  if (!form) return;

  const submitBtn = document.getElementById("submit-btn");
  const message = document.getElementById("form-message");
  const rows = document.getElementById("job-rows");

  function statusCell(job) {
    if (job.status === "finished" && job.audio_url) {
      return `<a class="text-indigo-600 hover:underline" href="${job.audio_url}" target="_blank">Download</a>`;
    }
    if (job.status === "failed") {
      return `<span class="text-red-600">${job.error || "failed"}</span>`;
    }
    return "&mdash;";
  }

  function upsertRow(job, textPreview, lang) {
    let row = rows.querySelector(`tr[data-job-id="${job.job_id}"]`);
    if (!row) {
      row = document.createElement("tr");
      row.dataset.jobId = job.job_id;
      row.className = "border-b border-slate-100 last:border-0";
      row.innerHTML = `
        <td class="px-4 py-2 max-w-xs truncate"></td>
        <td class="px-4 py-2"></td>
        <td class="px-4 py-2 job-status"></td>
        <td class="px-4 py-2 job-audio"></td>
        <td class="px-4 py-2 text-right">
          <button type="button" class="delete-job-btn text-red-600 hover:underline text-sm">Delete</button>
        </td>
      `;
      rows.prepend(row);
      row.children[0].textContent = textPreview;
      row.children[1].textContent = lang;
    }
    row.querySelector(".job-status").textContent = job.status;
    row.querySelector(".job-audio").innerHTML = statusCell(job);
  }

  function pollJob(jobId, textPreview, lang) {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/jobs/${jobId}`, { credentials: "same-origin" });
        if (!res.ok) {
          clearInterval(interval);
          return;
        }
        const job = await res.json();
        upsertRow(job, textPreview, lang);
        if (job.status === "finished" || job.status === "failed" || job.status === "expired") {
          clearInterval(interval);
        }
      } catch (err) {
        clearInterval(interval);
      }
    }, 2000);
  }

  // Resume polling for any jobs still in progress on initial page load.
  rows.querySelectorAll("tr[data-job-id]").forEach((row) => {
    const statusText = row.querySelector(".job-status").textContent.trim();
    if (statusText === "queued" || statusText === "started") {
      const textPreview = row.children[0].textContent;
      const lang = row.children[1].textContent;
      pollJob(row.dataset.jobId, textPreview, lang);
    }
  });

  rows.addEventListener("click", async (event) => {
    if (!event.target.classList.contains("delete-job-btn")) return;
    const row = event.target.closest("tr[data-job-id]");
    if (!row) return;

    event.target.disabled = true;
    try {
      const res = await fetch(`/api/v1/jobs/${row.dataset.jobId}`, {
        method: "DELETE",
        credentials: "same-origin",
      });
      if (res.ok || res.status === 404) {
        row.remove();
      } else {
        event.target.disabled = false;
      }
    } catch (err) {
      event.target.disabled = false;
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submitBtn.disabled = true;
    message.textContent = "Submitting...";

    const text = document.getElementById("text").value;
    const lang = document.getElementById("lang").value;
    const payload = {
      text,
      lang,
      voice: document.getElementById("voice").value,
      speed: parseFloat(document.getElementById("speed").value),
      steps: parseInt(document.getElementById("steps").value, 10),
    };

    try {
      const res = await fetch("/api/v1/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        message.textContent = "Error: " + (err.detail ? JSON.stringify(err.detail) : res.statusText);
        return;
      }

      const job = await res.json();
      message.textContent = "Queued.";
      upsertRow(
        { job_id: job.job_id, status: job.status, audio_url: null, error: null },
        text.slice(0, 200),
        lang
      );
      pollJob(job.job_id, text.slice(0, 200), lang);
      form.reset();
    } catch (err) {
      message.textContent = "Request failed.";
    } finally {
      submitBtn.disabled = false;
    }
  });
})();
