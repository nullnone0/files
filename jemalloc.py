from conans import AutoToolsBuildEnvironment, ConanFile, tools
from conans.errors import ConanInvalidConfiguration
import os
import shutil
import string


class JemallocConan(ConanFile):
    name = "jemalloc"
    version = "5.2.1"
    url = "https://github.com/jemalloc/jemalloc/releases/download/5.2.1/jemalloc-5.2.1.tar.bz2"
    settings = "cppstd", "os", "arch", "compiler", "build_type"
    default_settings = "cppstd=14"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "prefix": "ANY",
        "enable_cxx": [True, False],
        "enable_fill": [True, False],
        "enable_xmalloc": [True, False],
        "enable_readlinkat": [True, False],
        "enable_syscall": [True, False],
        "enable_lazy_lock": [True, False],
        "enable_debug_logging": [True, False],
        "enable_initial_exec_tls": [True, False],
        "enable_libdl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "prefix": "",
        "enable_cxx": True,
        "enable_fill": True,
        "enable_xmalloc": False,
        "enable_readlinkat": False,
        "enable_syscall": True,
        "enable_lazy_lock": False,
        "enable_debug_logging": False,
        "enable_initial_exec_tls": True,
        "enable_libdl": True,
    }

    _autotools = None

    _source_subfolder = "source_subfolder"

    def configure(self):
        if self.options.enable_cxx and \
                self.settings.compiler.get_safe("libcxx") == "libc++" and \
                self.settings.compiler == "clang" and \
                tools.Version(self.settings.compiler.version) < "10":
            raise ConanInvalidConfiguration("clang and libc++ version {} (< 10) is missing a mutex implementation".format(self.settings.compiler.version))
        if self.options.shared:
            del self.options.fPIC
        if not self.options.enable_cxx:
            del self.settings.compiler.libcxx
            del self.settings.compiler.cppstd
        if self.settings.build_type not in ("Release", "Debug", None):
            raise ConanInvalidConfiguration("Only Release and Debug build_types are supported")

    def source(self):
        tools.get(self.url, md5="3d41fbf006e6ebffd489bdb304d009ae")
        os.rename("{}-{}".format(self.name, self.version), self._source_subfolder)

    @property
    def _autotools_args(self):
        conf_args = [
            "--with-jemalloc-prefix={}".format(self.options.prefix),
            "--enable-debug" if self.settings.build_type == "Debug" else "--disable-debug",
            "--enable-cxx" if self.options.enable_cxx else "--disable-cxx",
            "--enable-fill" if self.options.enable_fill else "--disable-fill",
            "--enable-xmalloc" if self.options.enable_cxx else "--disable-xmalloc",
            "--enable-readlinkat" if self.options.enable_readlinkat else "--disable-readlinkat",
            "--enable-syscall" if self.options.enable_syscall else "--disable-syscall",
            "--enable-lazy-lock" if self.options.enable_lazy_lock else "--disable-lazy-lock",
            "--enable-log" if self.options.enable_debug_logging else "--disable-log",
            "--enable-initial-exec-tld" if self.options.enable_initial_exec_tls else "--disable-initial-exec-tls",
            "--enable-libdl" if self.options.enable_libdl else "--disable-libdl",
        ]
        conf_args.append("--enable-prof")
        if self.options.shared:
            conf_args.extend(["--enable-shared", "--disable-static"])
        else:
            conf_args.extend(["--disable-shared", "--enable-static"])
        return conf_args

    def _configure_autotools(self):
        if self._autotools:
            return self._autotools
        self._autotools = AutoToolsBuildEnvironment(self)
        self._autotools.configure(args=self._autotools_args, configure_dir=self._source_subfolder)
        return self._autotools

    def build(self):
        autotools = self._configure_autotools()
        autotools.make()

    @property
    def _library_name(self):
        libname = "jemalloc"
        if not self.options.shared and self.options.fPIC:
            libname += "_pic"
        return libname

    def package(self):
        self.copy(pattern="COPYING", src=self._source_subfolder, dst="licenses")
        autotools = self._configure_autotools()
        autotools.make(target="install_lib_shared" if self.options.shared else "install_lib_static")
        autotools.make(target="install_include")

    def package_id(self):
        if not self.settings.build_type:
            self.info.settings.build_type = "Release"

    def package_info(self):
        self.cpp_info.libs = [self._library_name]
        self.cpp_info.includedirs = [os.path.join(self.package_folder, "include"),
                                     os.path.join(self.package_folder, "include", "jemalloc")]
        if not self.options.shared:
            self.cpp_info.defines = ["JEMALLOC_EXPORT="]
