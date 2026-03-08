using System;
using System.IO;
using System.Numerics;
using Dalamud.Interface.Windowing;
using Dalamud.Bindings.ImGui;

namespace DalamudMBBBridge
{
    public class MBBConfigWindow : Window, IDisposable
    {
        private DalamudMBBBridge plugin;
        private string currentMbbPath = "";
        private bool showPathNotFoundWarning = false;

        public MBBConfigWindow(DalamudMBBBridge plugin) : base($"Magicite Babel Bridge v{DalamudMBBBridge.PluginVersion}###MBBBridge")
        {
            this.SizeConstraints = new WindowSizeConstraints
            {
                MinimumSize = new Vector2(450, 450),
                MaximumSize = new Vector2(800, 700)
            };

            this.plugin = plugin;
            this.IsOpen = false;

            // Initialize current path - no default, user must configure
            currentMbbPath = plugin.GetSavedMbbPath() ?? "";
        }

        public void Dispose()
        {
            // Clean up resources if needed
        }

        public override void Draw()
        {
            var mbbRunning = plugin.CheckMBBProcess();
            var connectionStatus = plugin.IsConnected ? "🟢 Connected" : "🟡 Waiting for connection";
            var mbbStatus = mbbRunning ? "🟢 Running" : "🔴 Not Running";

            // Status Section
            ImGui.TextColored(new Vector4(0.2f, 0.8f, 1.0f, 1.0f), "📊 Status");
            ImGui.Separator();
            ImGui.Spacing();

            ImGui.Text($"Bridge Status: {connectionStatus}");
            ImGui.Text($"MBB Application: {mbbStatus}");
            ImGui.Text($"Messages in Queue: {plugin.MessageQueueCount}");

            ImGui.Spacing();
            ImGui.Spacing();

            // Path Configuration Section
            ImGui.TextColored(new Vector4(0.8f, 0.6f, 1.0f, 1.0f), "📁 MBB Path Configuration");
            ImGui.Separator();
            ImGui.Spacing();

            var pathExists = File.Exists(currentMbbPath);
            if (!pathExists)
            {
                ImGui.PushStyleColor(ImGuiCol.Text, new Vector4(1.0f, 0.4f, 0.4f, 1.0f));
                ImGui.Text("⚠️ MBB.py not found at current path!");
                ImGui.PopStyleColor();
                showPathNotFoundWarning = true;
            }
            else
            {
                ImGui.TextColored(new Vector4(0.4f, 1.0f, 0.4f, 1.0f), "✅ MBB.py found");
                showPathNotFoundWarning = false;
            }

            ImGui.Text("MBB.py Path:");
            ImGui.SetNextItemWidth(-80);
            if (ImGui.InputText("##mbb_path", ref currentMbbPath, 500))
            {
                // Path was modified by user
            }

            ImGui.SameLine();
            if (ImGui.Button("Browse..."))
            {
                // Path suggestions for common installation locations
                var suggestions = new[]
                {
                    @"C:\MBB_Dalamud\python-app\MBB.py",
                    @"C:\MBB\python-app\MBB.py",
                    @"C:\MBB\MBB.exe",
                    @"C:\Users\" + Environment.UserName + @"\Downloads\MBB_Dalamud\python-app\MBB.py",
                    @"C:\Users\" + Environment.UserName + @"\Desktop\MBB_Dalamud\python-app\MBB.py"
                };

                ImGui.OpenPopup("Path Suggestions");
            }

            if (ImGui.BeginPopup("Path Suggestions"))
            {
                ImGui.Text("Common MBB.py locations:");
                ImGui.Separator();

                var suggestions = new[]
                {
                    @"C:\MBB_Dalamud\python-app\MBB.py",
                    @"C:\MBB\python-app\MBB.py",
                    @"C:\MBB\MBB.exe",
                    @"C:\Users\" + Environment.UserName + @"\Downloads\MBB_Dalamud\python-app\MBB.py",
                    @"C:\Users\" + Environment.UserName + @"\Desktop\MBB_Dalamud\python-app\MBB.py"
                };

                foreach (var suggestion in suggestions)
                {
                    if (ImGui.Selectable(suggestion))
                    {
                        currentMbbPath = suggestion;
                        ImGui.CloseCurrentPopup();
                    }

                    if (File.Exists(suggestion))
                    {
                        ImGui.SameLine();
                        ImGui.TextColored(new Vector4(0.4f, 1.0f, 0.4f, 1.0f), "✅");
                    }
                }

                ImGui.Separator();
                ImGui.Text("Manually edit the path above if your file is elsewhere.");
                ImGui.EndPopup();
            }

            ImGui.Spacing();

            if (ImGui.Button("💾 Save Path") && !string.IsNullOrEmpty(currentMbbPath))
            {
                if (File.Exists(currentMbbPath))
                {
                    plugin.SaveMbbPath(currentMbbPath);
                }
                else
                {
                    showPathNotFoundWarning = true;
                }
            }

            if (showPathNotFoundWarning)
            {
                ImGui.SameLine();
                ImGui.TextColored(new Vector4(1.0f, 0.4f, 0.4f, 1.0f), "File not found!");
            }

            ImGui.Spacing();
            ImGui.Spacing();

            // Control Section
            ImGui.TextColored(new Vector4(1.0f, 0.8f, 0.2f, 1.0f), "🎮 Controls");
            ImGui.Separator();
            ImGui.Spacing();

            // Always show Launch button
            ImGui.PushStyleColor(ImGuiCol.Button, new Vector4(0.2f, 0.8f, 0.2f, 1.0f));
            ImGui.PushStyleColor(ImGuiCol.ButtonHovered, new Vector4(0.3f, 0.9f, 0.3f, 1.0f));
            ImGui.PushStyleColor(ImGuiCol.ButtonActive, new Vector4(0.1f, 0.7f, 0.1f, 1.0f));

            if (ImGui.Button("Launch MBB Application", new Vector2(-1, 40)))
            {
                plugin.LaunchMBB();
            }

            ImGui.PopStyleColor(3);

            ImGui.Spacing();

            if (mbbRunning)
            {
                ImGui.TextColored(new Vector4(0.4f, 1.0f, 0.4f, 1.0f), "MBB is running normally");
            }
            else
            {
                ImGui.TextColored(new Vector4(1.0f, 0.4f, 0.4f, 1.0f), "MBB is not running");
            }

            ImGui.Spacing();

            if (ImGui.Button("Refresh Status", new Vector2(-1, 30)))
            {
                plugin.RefreshMBBStatus();
            }

            ImGui.Spacing();

            // Show Console Option
            var showConsole = plugin.ShowConsole;
            if (ImGui.Checkbox("Show Console Window (Debug)", ref showConsole))
            {
                plugin.ShowConsole = showConsole;
                plugin.SaveShowConsole();
            }
            if (ImGui.IsItemHovered())
            {
                ImGui.SetTooltip("Enable to show MBB console window for debugging.\nDefault: Hidden for cleaner experience.");
            }

            ImGui.Spacing();
            ImGui.Spacing();

            // Connection Details
            if (plugin.IsConnected)
            {
                ImGui.TextColored(new Vector4(0.4f, 1.0f, 0.4f, 1.0f), "Bridge Connection: Active");
                ImGui.Text("Real-time text capture is working");
            }
            else
            {
                ImGui.TextColored(new Vector4(1.0f, 0.6f, 0.2f, 1.0f), "Bridge Connection: Waiting");
                ImGui.Text("Enable 'Dalamud Mode' in MBB Settings");
            }

            ImGui.Spacing();
            ImGui.Spacing();

            // Instructions Section
            ImGui.TextColored(new Vector4(0.8f, 1.0f, 0.8f, 1.0f), "Setup Instructions");
            ImGui.Separator();
            ImGui.Spacing();

            ImGui.TextWrapped("1. Click 'Launch MBB Application' above");
            ImGui.TextWrapped("2. Enable 'Dalamud Mode' in MBB Settings");
            ImGui.TextWrapped("3. Press F9 to start translation");
            ImGui.TextWrapped("4. Talk to NPCs to see real-time translation");

            ImGui.Spacing();
            ImGui.Spacing();

            // Footer with Commands
            ImGui.Separator();
            ImGui.TextColored(new Vector4(0.7f, 0.7f, 0.7f, 1.0f), "Commands:");
            ImGui.SameLine();
            ImGui.Text("/mbb status");
            ImGui.SameLine();
            ImGui.Text("|");
            ImGui.SameLine();
            ImGui.Text("/mbb launch");
            ImGui.SameLine();
            ImGui.Text("|");
            ImGui.SameLine();
            ImGui.Text("/mbb help");
        }
    }
}