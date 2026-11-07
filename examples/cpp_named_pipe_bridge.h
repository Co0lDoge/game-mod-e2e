// ============================================================================
// Generic In-Engine Named Pipe Test Bridge Template (C++20 / Win32)
// ============================================================================
// Drop-in template for game mods. Hosts a background Named Pipe thread that
// marshals JSON commands onto the game's main/render thread via a mutex queue.
//
// Usage:
//   1. Call `test_bridge::Initialize(L"\\\\.\\pipe\\my_game_mcp_bridge", HandleCommand)`
//      when the mod loads (gated by `#ifdef ENABLE_TEST_BRIDGE`).
//   2. Call `test_bridge::OnFrameTick()` once per frame inside the game's
//      main update tick or hooked `Present()` call.
//   3. Call `test_bridge::Shutdown()` on plugin unload.
// ============================================================================

#pragma once

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <Windows.h>
#include <atomic>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <vector>

namespace test_bridge {

using CommandHandlerFn = std::function<std::string(const std::string& jsonRequest, uint64_t frameCount)>;

struct QueuedTask {
    std::string request;
    std::string response;
    bool completed = false;
};

class BridgeServer {
public:
    static BridgeServer& Instance() {
        static BridgeServer instance;
        return instance;
    }

    void Initialize(const std::wstring& pipeName, CommandHandlerFn handler) {
        if (m_running.exchange(true)) return;
        m_pipeName = pipeName;
        m_handler = std::move(handler);
        m_thread = std::thread(&BridgeServer::PipeWorkerLoop, this);
        m_thread.detach();
    }

    void Shutdown() {
        m_running.store(false);
        m_cv.notify_all();
    }

    // MUST be called exclusively on the game's main/render thread once per frame
    void OnFrameTick() {
        ++m_frameCount;
        std::unique_lock<std::mutex> lock(m_mutex);
        while (!m_queue.empty()) {
            QueuedTask* task = m_queue.front();
            m_queue.pop();
            lock.unlock();

            try {
                if (m_handler) {
                    task->response = m_handler(task->request, m_frameCount.load());
                } else {
                    task->response = R"({"ok":false,"error":"No command handler registered"})";
                }
            } catch (const std::exception& e) {
                task->response = std::string(R"({"ok":false,"error":")") + e.what() + "\"}";
            } catch (...) {
                task->response = R"({"ok":false,"error":"Unhandled exception on main thread"})";
            }

            lock.lock();
            task->completed = true;
            m_cv.notify_all();
        }
    }

    uint64_t GetFrameCount() const noexcept { return m_frameCount.load(); }

private:
    std::string ExecuteOnMainThread(const std::string& request, DWORD timeoutMs = 5000) {
        QueuedTask task{request, "", false};
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            m_queue.push(&task);
        }
        std::unique_lock<std::mutex> lock(m_mutex);
        if (!m_cv.wait_for(lock, std::chrono::milliseconds(timeoutMs), [&] { return task.completed || !m_running.load(); })) {
            return R"({"ok":false,"error":"Main thread execution timed out"})";
        }
        return task.response;
    }

    void PipeWorkerLoop() {
        while (m_running.load()) {
            HANDLE hPipe = CreateNamedPipeW(
                m_pipeName.c_str(),
                PIPE_ACCESS_DUPLEX,
                PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
                PIPE_UNLIMITED_INSTANCES,
                65536, 65536, 0, nullptr);

            if (hPipe == INVALID_HANDLE_VALUE) {
                Sleep(500);
                continue;
            }

            BOOL connected = ConnectNamedPipe(hPipe, nullptr) ? TRUE : (GetLastError() == ERROR_PIPE_CONNECTED);
            if (connected && m_running.load()) {
                std::vector<char> buffer(65536);
                DWORD bytesRead = 0;
                while (m_running.load() && ReadFile(hPipe, buffer.data(), static_cast<DWORD>(buffer.size() - 1), &bytesRead, nullptr) && bytesRead > 0) {
                    buffer[bytesRead] = '\0';
                    std::string req(buffer.data(), bytesRead);
                    std::string resp = ExecuteOnMainThread(req);
                    resp.push_back('\n');
                    DWORD bytesWritten = 0;
                    WriteFile(hPipe, resp.data(), static_cast<DWORD>(resp.size()), &bytesWritten, nullptr);
                    FlushFileBuffers(hPipe);
                }
            }
            DisconnectNamedPipe(hPipe);
            CloseHandle(hPipe);
        }
    }

    std::wstring m_pipeName;
    CommandHandlerFn m_handler;
    std::atomic<bool> m_running{false};
    std::atomic<uint64_t> m_frameCount{0};
    std::mutex m_mutex;
    std::condition_variable m_cv;
    std::queue<QueuedTask*> m_queue;
    std::thread m_thread;
};

} // namespace test_bridge
