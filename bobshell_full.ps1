# Parse command line arguments
param(
    [Parameter(Mandatory=$false)]
    [Alias("pm")]
    [ValidateSet("npm", "pnpm", "yarn", "")]
    [string]$PackageManager = ""
)

# Set execution policy for current process and child processes
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

# Color and symbol definitions
$script:Colors = @{
    Red     = [System.ConsoleColor]::Red
    Green   = [System.ConsoleColor]::Green
    Yellow  = [System.ConsoleColor]::Yellow
    Blue    = [System.ConsoleColor]::Blue
    Cyan    = [System.ConsoleColor]::Cyan
    White   = [System.ConsoleColor]::White
    Gray    = [System.ConsoleColor]::Gray
}

$script:Symbols = @{
    CheckMark = [char]::ConvertFromUtf32(0x2713)  # ✓
    CrossMark = [char]::ConvertFromUtf32(0x2717)  # ✗
    Arrow     = [char]::ConvertFromUtf32(0x2192)  # →
    Warning   = [char]::ConvertFromUtf32(0x26A0)  # ⚠
    Package   = [char]::ConvertFromUtf32(0x1F4E6) # 📦
    Download  = [char]::ConvertFromUtf32(0x2B07)  # ⬇
    Install   = [char]::ConvertFromUtf32(0x1F527) # 🔧
}

# Function to write colored output
function Write-ColorOutput {
    param(
        [string]$Message,
        [System.ConsoleColor]$ForegroundColor = [System.ConsoleColor]::White,
        [switch]$NoNewline
    )

    $previousColor = $Host.UI.RawUI.ForegroundColor
    $Host.UI.RawUI.ForegroundColor = $ForegroundColor

    if ($NoNewline) {
        Write-Host $Message -NoNewline
    } else {
        Write-Host $Message
    }

    $Host.UI.RawUI.ForegroundColor = $previousColor
}

# Helper functions for different message types
function Write-Info {
    param([string]$Message)
    Write-ColorOutput "$($script:Symbols.Arrow) " -ForegroundColor $script:Colors.Blue -NoNewline
    Write-Host $Message
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "$($script:Symbols.CheckMark) " -ForegroundColor $script:Colors.Green -NoNewline
    Write-Host $Message
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "$($script:Symbols.CrossMark) " -ForegroundColor $script:Colors.Red -NoNewline
    Write-Host $Message
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "$($script:Symbols.Warning)  " -ForegroundColor $script:Colors.Yellow -NoNewline
    Write-Host $Message
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-ColorOutput $Message -ForegroundColor $script:Colors.Cyan
    Write-Host ""
}

# Function to check if a command is available
function Test-CommandExists {
    param ($command)
    $exists = $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
    return $exists
}

# Function to check Node.js version
function Test-NodeVersion {
    Write-Header "Checking Node.js Installation"

    if (-not (Test-CommandExists "node")) {
        Write-Error "Node.js is not installed."
        Write-ColorOutput "  Please install Node.js version 22.15 or higher and try again." -ForegroundColor $script:Colors.Yellow
        exit 1
    }

    $nodeVersionOutput = node -v
    $nodeVersion = $nodeVersionOutput -replace '^v', ''
    $requiredVersion = [version]"22.15.0"
    $currentVersion = [version]$nodeVersion

    if ($currentVersion -lt $requiredVersion) {
        Write-Error "Node.js version $nodeVersion is installed, but version 22.15 or higher is required."
        Write-ColorOutput "  Please upgrade Node.js and try again." -ForegroundColor $script:Colors.Yellow
        exit 1
    }

    Write-Success "Node.js version $nodeVersion detected (minimum 22.15 required)"
}

# Check Node.js version first
Test-NodeVersion

# Package manager selection
Write-Header "Package Manager Selection"
Write-Host ""
if ($PackageManager -eq "") {
    Write-Info "Tip: You can skip this selection by using: -PackageManager or -pm (e.g., -pm npm)"
}

# Check which package managers are available
$availableManagers = @()
if (Test-CommandExists "npm") { $availableManagers += "npm" }
if (Test-CommandExists "pnpm") { $availableManagers += "pnpm" }
if (Test-CommandExists "yarn") { $availableManagers += "yarn" }

# Handle case where no package managers are available
if ($availableManagers.Count -eq 0) {
    Write-Error "No supported package managers (npm, pnpm, or yarn) found on your system."
    Write-ColorOutput "  Please install one of these package managers and try again." -ForegroundColor $script:Colors.Yellow
    exit 1
}

# Handle preselected package manager
$selected = ""
if ($PackageManager -ne "") {
    # Validate that the preselected package manager is available
    if ($availableManagers -contains $PackageManager) {
        $selected = $PackageManager
        Write-Info "Using preselected package manager: $selected"
    }
    else {
        Write-Error "Preselected package manager '$PackageManager' is not available."
        Write-ColorOutput "  Available options: $($availableManagers -join ', ')" -ForegroundColor $script:Colors.Yellow
        exit 1
    }
}
# If only one package manager is available, use it automatically
elseif ($availableManagers.Count -eq 1) {
    $selected = $availableManagers[0]
    Write-Info "Only $selected is available. Using it automatically."
}
# If multiple package managers are available, let the user choose
else {
    Write-ColorOutput "Available package managers:" -ForegroundColor $script:Colors.Cyan
    Write-Host ""

    # Display only available package managers
    $index = 1
    $optionMap = @{}

    foreach ($manager in $availableManagers) {
        Write-Host "  $index) " -NoNewline
        Write-ColorOutput $manager -ForegroundColor $script:Colors.White
        $optionMap[$index.ToString()] = $manager
        $index++
    }

    Write-Host ""

    # Read user input directly from console device
    $maxOption = $availableManagers.Count

    while ($selected -eq "") {
        Write-Host "Enter your choice (1-$maxOption): " -NoNewline -ForegroundColor $script:Colors.White
        $choice = Read-Host

        if ($optionMap.ContainsKey($choice)) {
            $selected = $optionMap[$choice]
            Write-Success "Selected $selected"
        }
        else {
            Write-Error "Invalid selection. Please enter a number between 1 and $maxOption."
        }
    }
}

Write-Host ""
Write-Header "Downloading bobshell"

# Fetch version with progress indicator
Write-Info "Fetching latest version..."

try {
    $version = (Invoke-WebRequest -Uri "https://s3.us-south.cloud-object-storage.appdomain.cloud/bob-shell/bobshell-version.txt" -UseBasicParsing).Content.Trim()

    if ([string]::IsNullOrWhiteSpace($version)) {
        Write-Error "Failed to fetch bobshell version"
        exit 1
    }

    Write-Success "Latest version: $version"
}
catch {
    Write-Error "Failed to fetch bobshell version: $_"
    exit 1
}

$dl_url = "https://s3.us-south.cloud-object-storage.appdomain.cloud/bob-shell/bobshell-${version}.tgz"

Write-Host ""
Write-Header "Installing bobshell"
Write-Info "Installing bobshell $version with $selected..."
Write-Host ""

# Function to show spinner during installation
function Show-Spinner {
    param(
        [System.Diagnostics.Process]$Process
    )

    $spinChars = @([char]0x280B, [char]0x2819, [char]0x2839, [char]0x2838, [char]0x283C, [char]0x2834, [char]0x2826, [char]0x2827, [char]0x2807, [char]0x280F)
    $i = 0

    while (-not $Process.HasExited) {
        $spinChar = $spinChars[$i % $spinChars.Length]
        Write-Host "`r " -NoNewline
        Write-ColorOutput "$spinChar" -ForegroundColor $script:Colors.Cyan -NoNewline
        Write-Host "  Installing...   " -NoNewline
        Start-Sleep -Milliseconds 100
        $i++
    }
    Write-Host "`r                                        `r" -NoNewline
}

# Install using the selected package manager
$installSuccess = $false

try {
    $logFileOut = Join-Path $env:TEMP "bobshell-install-out.log"
    $logFileErr = Join-Path $env:TEMP "bobshell-install-err.log"

    # Get the actual command path and extension to handle .cmd, .bat, .ps1, and .exe files
    $cmdInfo = Get-Command $selected -ErrorAction Stop
    $cmdPath = $cmdInfo.Source
    $extension = [System.IO.Path]::GetExtension($cmdPath).ToLower()

    # Build arguments based on package manager
    $installArgs = @()
    switch ($selected) {
        "pnpm" {
            $installArgs = @("add", "--reg=https://registry.npmjs.org/", "-g", $dl_url)
        }
        "npm" {
            $installArgs = @("install", "--reg=https://registry.npmjs.org/", "--progress=false", "--loglevel=error", "-g", $dl_url)
        }
        "yarn" {
            $Env:YARN_REGISTRY = "https://registry.npmjs.org/"
            $installArgs = @("global", "add", "--silent", $dl_url)
        }
    }

    # Determine how to execute based on file type (Windows-specific handling)
    $processPath = ""
    $processArgs = @()

    switch ($extension) {
        { $_ -in '.cmd', '.bat' } {
            # Batch files need cmd.exe
            $processPath = "cmd.exe"
            $processArgs = @('/c', "`"$cmdPath`"") + $installArgs
        }
        '.ps1' {
            # PowerShell scripts need powershell.exe
            $processPath = "powershell.exe"
            $processArgs = @('-ExecutionPolicy', 'Bypass', '-File', "`"$cmdPath`"") + $installArgs
        }
        default {
            # Assume it's a native executable (.exe)
            $processPath = $cmdPath
            $processArgs = $installArgs
        }
    }

    $process = Start-Process -FilePath $processPath -ArgumentList $processArgs -NoNewWindow -PassThru -RedirectStandardOutput $logFileOut -RedirectStandardError $logFileErr
    Show-Spinner -Process $process
    $process.WaitForExit()

    # Verify installation properly instead of relying on exit code
    if (Test-CommandExists "bob") {
        try {
            $versionOutput = & bob --version 2>$null
            $installedVersion = ($versionOutput | Select-Object -Last 1).Trim()
            if ($installedVersion -eq $version) {
                $installSuccess = $true
            }
            else {
                Write-Warning "Version mismatch: installed $installedVersion, expected $version"
            }
        }
        catch {
            Write-Warning "bob command exists but version check failed: $_"
        }
    }
}
catch {
    Write-Error "Installation failed: $_"
}

Write-Host ""
if ($installSuccess) {
    Write-Header "Installation Complete! $($script:Symbols.CheckMark)"
    Write-Success "bobshell $version has been successfully installed"
    Write-Host ""
    Write-Info "You can now run: bob"
    Write-Host ""

    # Telemetry Notice for External Users
    Write-ColorOutput "Usage data is collected by default." -ForegroundColor $script:Colors.Cyan
    Write-Host ""
    Write-Info "To opt out, type /settings, navigate to Enable Usage Metrics and set the flag to false"
    Write-Host ""

    # Clean up log files
    if (Test-Path $logFileOut) { Remove-Item $logFileOut -Force -ErrorAction SilentlyContinue }
    if (Test-Path $logFileErr) { Remove-Item $logFileErr -Force -ErrorAction SilentlyContinue }
}
else {
    Write-Error "Installation failed"
    Write-Host ""

    # Show error logs if they exist
    if (Test-Path $logFileErr) {
        $errorContent = Get-Content $logFileErr -Raw -Encoding UTF8
        if (-not [string]::IsNullOrWhiteSpace($errorContent)) {
            Write-ColorOutput "Error details:" -ForegroundColor $script:Colors.Red
            Write-Output $errorContent
        }
        Remove-Item $logFileErr -Force -ErrorAction SilentlyContinue
    }

    if (Test-Path $logFileOut) {
        $errorContent = Get-Content $logFileOut -Raw -Encoding UTF8
        if (-not [string]::IsNullOrWhiteSpace($errorContent)) {
            Write-ColorOutput "Error details:" -ForegroundColor $script:Colors.Red
            Write-Output $errorContent
        }
        Remove-Item $logFileOut -Force -ErrorAction SilentlyContinue
    }

    exit 1
}

exit 0
