import { Html5Qrcode } from "html5-qrcode";

window.onload = () => {
    const qrReader = new Html5Qrcode("reader");
    qrReader
        .start(
            { facingMode: "environment" }, // Use rear camera
            {
                fps: 10,
                qrbox: { width: 250, height: 250 }, // Scanning area
            },
            (decodedText) => {
                qrReader.stop();
                document.getElementById("result").textContent = `Scanned Code: ${decodedText}`;
                window.location.href = `/search-product/?code=${decodedText}`;
            },
            (errorMessage) => {
                console.warn(`Error scanning QR Code: ${errorMessage}`);
            }
        )
        .catch((err) => {
            console.error(`Unable to start QR Scanner: ${err}`);
            document.getElementById("result").textContent = "Camera access denied or unavailable.";
        });
};
