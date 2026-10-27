<?php

namespace SpondonIt\SchoolService\Lifecycle;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * SchoolLifecycle.php
 */

class SchoolLifecycle implements SpondonIt\Service\Contracts\AppLifecycleInterface {
    public function afterAppInstall(array $params): void {
        $appUrl = appUrl();
        updateEnvFile([
            'APP_URL' => $appUrl,
            'ASSET_URL' => $appUrl,
            'APP_ENV' => 'production',
            'APP_DEBUG' => 'false',
        ]);
    }

    public function afterModuleInstall(string $name, array $params, array $response): void {
    }

    public function afterModuleDisable(string $name): void {
    }

    public function afterModuleRevoke(string $name): void {
    }

    public function afterThemeInstall(string $name, array $params, array $response): void {
    }

    public function afterThemeRevoke(string $name): void {
    }

    public function afterUninstall(): void {
    }
}
