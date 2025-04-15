const recordButton = document.getElementById('record');
const stopButton = document.getElementById('stop');
const audioElement = document.getElementById('audio');
const uploadForm = document.getElementById('uploadForm');
const audioDataInput = document.getElementById('audioData');
const timerDisplay = document.getElementById('timer');

let mediaRecorder;
let audioChunks = [];
let startTime;

function formatTime(time) {
  const minutes = Math.floor(time / 60);
  const seconds = Math.floor(time % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

document.getElementById('uploadButton').addEventListener('click', function() {
  const formData = new FormData();
  const fileInput = document.getElementById('fileUpload');
  console.log('Reached here')
  if (fileInput.files.length > 0) {
      formData.append('book_file', fileInput.files[0]);

      fetch('/upload_book', {
          method: 'POST',
          body: formData
      })
      .then(response => response.json())
      .then(data => console.log(data))
      .catch(error => console.error('Error:', error));
  } else {
      alert('Please select a file to upload.');
  }
});

recordButton.addEventListener('click', () => {
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.start();

      startTime = Date.now();
      let timerInterval = setInterval(() => {
        const elapsedTime = Math.floor((Date.now() - startTime) / 1000);
        timerDisplay.textContent = formatTime(elapsedTime);
      }, 1000);

      mediaRecorder.ondataavailable = e => {
        audioChunks.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const formData = new FormData();
        formData.append('audio_data', audioBlob, 'recorded_audio.wav');

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            location.reload(); // Force refresh

            return response.text();
        })
        .then(data => {
            console.log('Audio uploaded successfully:', data);
            // Redirect to playback page or display success message
        })
        .catch(error => {
            console.error('Error uploading audio:', error);
        });
      };
    })
    .catch(error => {
      console.error('Error accessing microphone:', error);
    });

  recordButton.disabled = true;
  stopButton.disabled = false;
});

stopButton.addEventListener('click', () => {
    console.log("Look here!")
  if (mediaRecorder) {
    mediaRecorder.stop();

    timerDisplay.textContent = '00:00 - processing...';
  }

  recordButton.disabled = false;
  stopButton.disabled = true;
});

// Initially disable the stop button
stopButton.disabled = true;