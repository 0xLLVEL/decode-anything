<?php

namespace SpondonIt\Service\Contracts;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Contracts\AppLifecycleInterface.php
 */

interface AppLifecycleInterface {
    public function afterAppInstall(array $params): void;

    public function afterModuleInstall(string $name, array $params, array $response): void;

    public function afterModuleDisable(string $name): void;

    public function afterModuleRevoke(string $name): void;

    public function afterThemeInstall(string $name, array $params, array $response): void;

    public function afterThemeRevoke(string $name): void;

    public function afterUninstall(): void;
}
