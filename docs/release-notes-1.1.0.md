# Lumina Desk 1.1.0

## 新增

- **自定义挂件背景**：设置 → 背景 → 选择图片。
- 图片比例和挂件不一致时，会打开取景对话框：
  - 拖动画面平移取景；
  - 拖动四角按挂件比例缩放；
  - 双击恢复默认取景；
  - 只裁切、不拉伸，原图不会被修改。
- 裁切结果保存为 `%APPDATA%\LuminaDesk\background-*.png`，换电脑前可以随数据目录一起备份。
- 深色和浅色主题都会自动加一层可读性遮罩，背景照片不会盖住时间与天气文字。

## 保持

- 背景透明度仍然只作用于挂件卡片；文字保持清晰。
- 便签的类别配色与自定义背景互不影响。
- 可随时在设置里「恢复默认」，回到原有渐变背景。

## 升级

直接下载并替换旧的 `LuminaDesk.exe` 即可。配置和便签数据会保留。

下载：[LuminaDesk.exe](https://github.com/LilSeven/LuminaDesk/releases/download/v1.1.0/LuminaDesk.exe)

## 校验

- Windows 10/11 x64，单文件 exe，无需安装 Python。
- 数据目录：`%APPDATA%\LuminaDesk\`
