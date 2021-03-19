# Introduction #

This project downloads or mirrors various registries locally.

These packages serve as a snapshot of the registries for malware analysis purpose, 
as well as for speeding up data downloading in analysis phase.


# Cloud Storage FUSE #

- [Introduction to cloud storage fuse](https://cloud.google.com/storage/docs/gcs-fuse)
    - [Install cloud storage fuse](https://github.com/GoogleCloudPlatform/gcsfuse/blob/master/docs/installing.md)


# HowTo #

- See BUILD.md


# Reference #

- [latest registry stats](http://www.modulecounts.com)
- [add package manager to libraries.io](https://github.com/librariesio/libraries.io/blob/ffbb032c53b3f8354d9245d67163869d97606c82/docs/add-a-package-manager.md)
- mirror npm: use download_npm.py
    - Total npm: 743189 packages, 5941465 tarballs
- mirror pypi: use [bandersnatch](https://pypi.org/project/bandersnatch/)
    - Total pypi: 146,190 projects 1,026,149 releases, [link](https://pypi.org)
- mirror rubygems: use [rubygems-mirror](https://github.com/rubygems/rubygems-mirror)
    - Total gems: 144964 packages, 1049481 gems
    - mirror configuration: ~/.gem/.mirrorrc
    - URL format: http://rubygems.org/quick/Marshal.4.8/rpaste-0.1.1.gemspec.rz
- mirror packagist: use [packagist-mirror-docker](https://github.com/Webysther/packagist-mirror-docker), [packagist-mirror](https://github.com/Webysther/packagist-mirror)
    - Total packagist: 189,294 packages, 1,289,515 versions, [link](https://packagist.org/statistics)
    - Unlike other package managers, packagist downloads packages from github/bitbucket directly. Therefore, mirrors are only for their json (metadata) files
    - [Composer registry manager](https://github.com/slince/composer-registry-manager)
    - [Composer 国内加速：可用镜像列表](https://learnku.com/php/wikis/30594)
- mirror maven: use [maven-mirror](https://maven.apache.org/guides/mini/guide-mirror-settings.html)
    - Total maven: 239,993 packages, 2,949,316 versions, [link](http://www.maven.org/#stats)
- mirror nuget: [NuGet v3 catalog reader](https://github.com/emgarten/NuGet.CatalogReader)
    - [NuGetMirror](https://www.nuget.org/packages/NuGetMirror/) 
    - [nuget mirror command](https://docs.microsoft.com/en-us/nuget/tools/cli-ref-mirror)
- mirror cocoapods
    - CocoaPods is a dependency manager for Swift and Objective-C Cocoa projects
    - [It has over 81 thousand libraries and is used in over 3 million apps](https://cocoapods.org/)
- mirror go packages
    - [go.dev is the hub for Go users providing centralized and curated resources](https://pkg.go.dev/)
- mirror wordpress plugins
    - [Extend your WordPress experience with 58,581 plugins](https://wordpress.org/plugins/)
- mirror debian packages
    - [Debian packages](https://www.debian.org/distrib/packages)
- mirror ubuntu packages
    - [Ubuntu packages](https://packages.ubuntu.com/)
    - [Ubuntu snapstore, similar to windows store](https://snapcraft.io/store)
- mirror centos packages
    - [CentOS packages](http://mirror.centos.org/centos/7/os/x86_64/Packages/)
- mirror archlinux packages
    - [ArchLinux user repository](https://aur.archlinux.org/)
- ignore mirror jcenter
    - [JFrog to Shut down JCenter and Bintray](https://www.infoq.com/news/2021/02/jfrog-jcenter-bintray-closure/)
    - [Bintray jcenter](https://bintray.com/bintray/jcenter)

