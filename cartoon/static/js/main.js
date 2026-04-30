document.addEventListener('DOMContentLoaded', () => {
    const imageInput = document.getElementById('imageInput');
    const dropZone = document.getElementById('dropZone');
    const cartoonizeBtn = document.getElementById('cartoonizeBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const originalPreview = document.getElementById('originalPreview');
    const cartoonPreview = document.getElementById('cartoonPreview');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const resultMeta = document.getElementById('resultMeta');

    let selectedFile = null;

    imageInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#ff4b4b';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = '#444';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#444';
        handleFiles(e.dataTransfer.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            selectedFile = files[0];
            const reader = new FileReader();
            reader.onload = (e) => {
                originalPreview.innerHTML = `<img src="${e.target.result}" alt="Original">`;
                cartoonizeBtn.disabled = false;
            };
            reader.readAsDataURL(selectedFile);
        }
    }

    cartoonizeBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        loadingOverlay.style.display = 'flex';

        const formData = new FormData();
        formData.append('image', selectedFile);

        try {
            const response = await fetch('/cartoonize', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.cartoon_image) {
                const imgUrl = `data:image/jpeg;base64,${data.cartoon_image}`;
                cartoonPreview.innerHTML = `<img src="${imgUrl}" alt="Cartoon">`;
                const modelInfo = data.model ? ` | model: ${data.model}` : '';
                const warningInfo = data.warning ? `<br>${data.warning}` : '';
                resultMeta.innerHTML = `backend: ${data.backend || 'unknown'}${modelInfo}${warningInfo}`;
                resultMeta.style.display = 'block';

                downloadBtn.style.display = 'inline-block';
                downloadBtn.onclick = () => {
                    const link = document.createElement('a');
                    link.href = imgUrl;
                    link.download = 'cartoonized_image.jpg';
                    link.click();
                };
            } else {
                alert(`Error: ${data.error || 'Failed to transform image'}`);
                resultMeta.style.display = 'none';
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Connection failed. Is the server running?');
            resultMeta.style.display = 'none';
        } finally {
            loadingOverlay.style.display = 'none';
        }
    });
});
