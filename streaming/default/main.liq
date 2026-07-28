# Liquidsoap Configuration

settings.log.level := 3

# Force Liquidsoap to listen on all network interfaces
settings.harbor.bind_addrs := ["0.0.0.0"]

# Loop message continuously
audio = single("streaming/default/message.wav")

# Stream MP3 over HTTP on port 8080
output.harbor(
  %mp3,
  port = 8080,
  mount = "/station",
  audio
)
