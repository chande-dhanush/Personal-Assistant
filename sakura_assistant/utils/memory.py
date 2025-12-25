import gc
import torch

def cleanup_memory():
    """
    Aggressive memory cleanup for PyTorch and Python GC.
    """
    # Python GC
    gc.collect()

    # CUDA
    try:
        if hasattr(torch, 'cuda') and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except:
        pass

    # CPU Arena (PyTorch >= 2.3)
    try:
        # Undocumented internal API for freeing CPU allocator cache
        if hasattr(torch, '_C') and hasattr(torch._C, '_foreach_tensor_cpu_empty_cache'):
             torch._C._foreach_tensor_cpu_empty_cache()
    except:
        pass

    # MPS (Apple Silicon)
    try:
        if hasattr(torch, 'mps'):
            torch.mps.empty_cache()
    except:
        pass
