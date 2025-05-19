// Main.js - Client side functionality for News Sentiment Analyzer

document.addEventListener('DOMContentLoaded', function() {
    // Form submission handler with loading indicator
    const analyzeForm = document.getElementById('analyzeForm');
    const analyzeButton = document.getElementById('analyzeButton');
    const analyzeSpinner = document.getElementById('analyzeSpinner');

    if (analyzeForm) {
        analyzeForm.addEventListener('submit', function() {
            // Show loading spinner
            if (analyzeButton && analyzeSpinner) {
                analyzeButton.disabled = true;
                analyzeButton.innerHTML = 'Analyzing... <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
            }
        });
    }

    // Report download functionality
    const downloadButton = document.getElementById('downloadReport');
    if (downloadButton) {
        downloadButton.addEventListener('click', function() {
            generatePDF();
        });
    }
});

// Function to generate and download a PDF report
function generatePDF() {
    // Alert for demo purposes
    alert('PDF Report generation would be implemented here in a production environment.');

    // In a real implementation, you would:
    // 1. Collect all the analysis data
    // 2. Use a library like jsPDF or call a server endpoint to generate PDF
    // 3. Trigger the download

    console.log('PDF report download requested');
}