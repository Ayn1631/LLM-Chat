import re
import tqdm
import PyPDF2
import pandas as pd

class Reader:
    def __init__(self, corpus_path: str):
        self.corpus = self.extract_pdf_page_text(corpus_path)

    def extract_pdf_page_text(self, filepath, max_len=256, overlap_len=0):
        page_content  = []
        with open(filepath, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in tqdm.tqdm(pdf_reader.pages, desc='解析PDF文件...'):
                page_text = page.extract_text().strip()
                raw_text = [text.strip() for text in page_text.split('\n')]
                new_text = '\n'.join(raw_text)
                new_text = re.sub(r'\n\d{2,3}\s?', '\n', new_text)
                if len(new_text) > 10 and '..............' not in new_text:
                    page_content.append(new_text)

        cleaned_chunks = []
        i = 0
        # 暴力将整个pdf当做一个字符串，然后按照固定大小的滑动窗口切割
        all_str = ''.join(page_content)
        all_str = all_str.replace('\n', '')
        while i < len(all_str):
            cur_s = all_str[i:i+max_len]
            if len(cur_s) > 10:
                cleaned_chunks.append(cur_s)
            i += (max_len - overlap_len)

        return page_content

if __name__ == '__main__':
    import os
    print(os.getcwd())
    reader = Reader('data/train_a.pdf')
    with open('data/train_a.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(reader.corpus))