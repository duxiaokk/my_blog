using System;
using Microsoft.Data.Sqlite;

var cs = new SqliteConnectionStringBuilder { DataSource = @"d:\Python\Personal Blog\my_blog\blog.db" }.ToString();
using var conn = new SqliteConnection(cs);
conn.Open();
using var cmd = conn.CreateCommand();
cmd.CommandText = "select id, title, content, created_at, like_count from posts where id = 3";
using var reader = cmd.ExecuteReader();
while (reader.Read())
{
    Console.WriteLine($"id={reader.GetInt32(0)}");
    Console.WriteLine($"title={reader.IsDBNull(1) ? "<null>" : reader.GetString(1)}");
    Console.WriteLine($"content={reader.IsDBNull(2) ? "<null>" : reader.GetString(2)}");
    Console.WriteLine($"created_at={reader.GetValue(3)}");
    Console.WriteLine($"like_count={reader.GetValue(4)}");
}
