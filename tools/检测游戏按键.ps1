Add-Type @"
using System.Runtime.InteropServices;
public static class RailKeys {
 [DllImport("user32.dll")] public static extern short GetAsyncKeyState(int key);
}
"@
$watch=[Diagnostics.Stopwatch]::StartNew()
$previous=''
while($watch.Elapsed.TotalSeconds -lt 90){
 $current=-join (@(65,68,70,72,74,75,83) | Where-Object { ([RailKeys]::GetAsyncKeyState($_) -band 0x8000) -ne 0 } | ForEach-Object { [char]$_ })
 if($current -ne $previous){ '{0:N3} {1}' -f $watch.Elapsed.TotalSeconds,$current; $previous=$current }
 Start-Sleep -Milliseconds 10
}

