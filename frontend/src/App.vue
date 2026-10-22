<template>
  <el-container style="min-height: 100vh">
    <el-header style="background: #1f4e9c; display: flex; align-items: center">
      <span style="color: #fff; font-size: 18px; font-weight: bold; margin-right: 32px">
        项目台账 · 一项目一本账
      </span>
      <el-menu :default-active="$route.path" mode="horizontal" router
               background-color="#1f4e9c" text-color="#dbe7f7"
               active-text-color="#ffffff" style="border: none">
        <el-menu-item index="/">项目列表</el-menu-item>
        <el-menu-item index="/stats">三口径统计</el-menu-item>
      </el-menu>
    </el-header>
    <el-main><router-view /></el-main>
  </el-container>
</template>
