# Local AI Build Process

The authoritative production build path is integrated into the primary OS compiler:
`scripts/build/build-iso.sh`

The Local AI inference engine (`llama.cpp`) is pinned strictly to `b11429` (`d812350`).
It is compiled directly inside the Debian `live-build` isolated environment using the following constraint flags to ensure CPU-only execution without assuming host-specific vector extensions:
`GGML_CUDA=OFF GGML_VULKAN=OFF GGML_METAL=OFF GGML_NATIVE=OFF`

The Qwen3-1.7B-Q4_K_M.gguf model is verified against its SHA256 checksum during the build process before being packaged into the final ISO.
