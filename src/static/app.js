const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const clearBtn = document.getElementById('clearBtn');
const printBtn = document.getElementById('printBtn');
const btnText = printBtn.querySelector('.btn-text');
const spinner = printBtn.querySelector('.spinner');
const statusContent = document.getElementById('statusContent');
const serviceStatus = document.getElementById('serviceStatus');

let currentFile = null;

function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function setStatus(type, message) {
    statusContent.className = 'status-content ' + type;
    statusContent.textContent = message;
}

function clearStatus() {
    statusContent.className = 'status-content';
    statusContent.textContent = '';
}

function updateFileDisplay() {
    if (!currentFile) {
        fileInfo.style.display = 'none';
        printBtn.disabled = true;
        return;
    }
    fileName.textContent = currentFile.name;
    fileSize.textContent = formatSize(currentFile.size);
    fileInfo.style.display = 'flex';
    printBtn.disabled = false;
}

function handleFile(file) {
    if (!file) return;
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        setStatus('error', '请选择 PDF 文件');
        return;
    }
    if (file.size > 50 * 1024 * 1024) {
        setStatus('error', '文件大小超过 50MB 限制');
        return;
    }
    currentFile = file;
    clearStatus();
    updateFileDisplay();
}

dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    handleFile(e.target.files[0]);
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    handleFile(e.dataTransfer.files[0]);
});

clearBtn.addEventListener('click', () => {
    currentFile = null;
    fileInput.value = '';
    updateFileDisplay();
    clearStatus();
});

async function pollTask(jobId) {
    const maxAttempts = 60;
    for (let i = 0; i < maxAttempts; i++) {
        await new Promise(r => setTimeout(r, 1000));
        try {
            const res = await fetch(`/api/tasks/${jobId}`);
            const data = await res.json();
            if (data.status === 'done') {
                setStatus('success', `打印成功！任务 ID: ${jobId}`);
                return;
            }
            if (data.status === 'failed') {
                setStatus('error', `打印失败：${data.message || '未知错误'}`);
                return;
            }
            setStatus('info', `正在打印... 当前状态：${data.status}`);
        } catch (err) {
            console.error(err);
        }
    }
    setStatus('error', '打印状态查询超时');
}

printBtn.addEventListener('click', async () => {
    if (!currentFile) return;

    printBtn.disabled = true;
    btnText.textContent = '打印中...';
    spinner.style.display = 'inline-block';
    clearStatus();
    setStatus('info', '正在提交打印任务...');

    const formData = new FormData();
    formData.append('file', currentFile);

    try {
        const res = await fetch('/api/print', {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.error || '提交失败');
        }

        setStatus('info', `任务已提交：${data.job_id}，等待打印结果...`);
        await pollTask(data.job_id);
    } catch (err) {
        setStatus('error', err.message);
    } finally {
        printBtn.disabled = false;
        btnText.textContent = '开始打印';
        spinner.style.display = 'none';
    }
});

async function checkService() {
    try {
        const res = await fetch('/api/status');
        if (res.ok) {
            serviceStatus.textContent = '服务在线';
            serviceStatus.classList.add('online');
        } else {
            throw new Error('offline');
        }
    } catch (err) {
        serviceStatus.textContent = '服务离线';
        serviceStatus.classList.remove('online');
    }
}

checkService();
setInterval(checkService, 5000);
