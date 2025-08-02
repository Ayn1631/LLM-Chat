from docx import Document
from tqdm import tqdm
from docx.oxml import OxmlElement
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl

def normalize_text(text):
    """标准化文本，去除多余空格和换行"""
    return ' '.join(text.split())

def read_docx(file_path):
    # 打开文档
    doc = Document(file_path)
    res = ''
    seen_content = set()  # 用于记录已解析的内容，避免重复

    print("文档内容：")
    for element in tqdm(doc.element.body):
        if element.tag.endswith('p'):  # 如果是段落
            para = ''.join(node.text for node in element.iter() if node.text).strip()
            normalized_para = normalize_text(para)
            if normalized_para and normalized_para not in seen_content:
                res += normalized_para + '\n'
                seen_content.add(normalized_para)
        elif element.tag.endswith('tbl'):  # 如果是表格
            table = next((tbl for tbl in doc.tables if tbl._element == element), None)
            if table:
                for row in table.rows:
                    row_text = '\t'.join(normalize_text(cell.text) for cell in row.cells)
                    if row_text and row_text not in seen_content:
                        res += row_text + '\n'
                        seen_content.add(row_text)

    return res

# 使用示例
if __name__ == '__main__':
    name = '布洛芬'
    res = read_docx(rf"D:\Mypower\Git\MyPython\大学\NLP\project\books\{name}.docx")

    with open(fr'D:\Mypower\Git\MyPython\大学\NLP\project\books\{name}.txt', 'w', encoding='utf-8') as f:
        f.write(res)